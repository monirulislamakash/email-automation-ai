from flask import Blueprint, jsonify, request
from src.site.routers.auth import token_required
from src.database.services.lead_services import (
    add_lead_db,
    get_all_leads,
    get_lead_by_lead_id,
    get_lead_by_db_id,
    delete_lead_by_db_id,
    delete_lead_by_lead_id,
    update_lead,
)
from src.database.models import Leads
from src.email.lead_manager import create_lead, delete_lead, update_instantly_lead
from src.email.campaign_manager import create_campaign as create_instantly_campaign
from src.database.services.campaign_services import get_campaign, get_campaign_db_id, get_all_campaigns, update_db_campaign

lead = Blueprint("lead", __name__)


def _looks_like_uuid(value):
    text = str(value or "").strip()
    return len(text) == 36 and "-" in text


def _resolve_campaign_for_request(requested_campaign_id):
    campaign = get_campaign(requested_campaign_id)
    if campaign:
        return campaign

    # Backward compatibility: some requests may pass the external Instantly id.
    all_campaigns = get_all_campaigns() or []
    for item in all_campaigns:
        options = item.options_settings if isinstance(item.options_settings, dict) else {}
        instantly_campaign_id = str(options.get("instantly_campaign_id") or "").strip()
        if instantly_campaign_id and instantly_campaign_id == str(requested_campaign_id):
            return item
    return None


def _extract_instantly_lead_id(payload):
    """Extract lead id from Instantly response variants."""
    if not isinstance(payload, dict):
        return None

    candidates = [
        payload.get("id"),
        payload.get("lead_id"),
        payload.get("leadId"),
    ]

    data = payload.get("data")
    if isinstance(data, dict):
        candidates.extend([data.get("id"), data.get("lead_id"), data.get("leadId")])

    leads = payload.get("leads")
    if isinstance(leads, list) and leads and isinstance(leads[0], dict):
        candidates.extend([leads[0].get("id"), leads[0].get("lead_id"), leads[0].get("leadId")])

    for candidate in candidates:
        if candidate is None:
            continue
        text = str(candidate).strip()
        if text:
            return text
    return None


def _ensure_external_lead_id(lead_row):
    """Backfill missing lead_id by creating/retrieving Instantly lead."""
    if not lead_row or lead_row.lead_id:
        return lead_row
    try:
        instantly_lead = create_lead(
            campaign_id=lead_row.campaign_id,
            lead_email=lead_row.email,
            first_name=lead_row.first_name or "",
            last_name=lead_row.last_name or "",
        )
        instantly_lead_id = _extract_instantly_lead_id(instantly_lead)
        if instantly_lead_id:
            update_lead(
                db_id=lead_row.id,
                lead_id=instantly_lead_id,
                lead_status=lead_row.lead_status if lead_row.lead_status is not None else 1,
                email_status=lead_row.email_status or "NOT Yet Contacted",
            )
            lead_row.lead_id = instantly_lead_id
    except Exception as e:
        print(f"Lead id backfill skipped for db_id={getattr(lead_row, 'id', None)}: {str(e)}")
    return lead_row


@lead.route("/api/app/lead/", methods=["POST"], strict_slashes=False)
@token_required
def lead_create(current_user):
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"message": "Missing JSON data"}), 400
        print("Lead Data: ", data)
        print()
        requested_campaign_id = data.get("campaign_id") or data.get("campaignId") or data.get("Campaign ID")
        if not requested_campaign_id:
            return jsonify({"message": "campaign_id is required"}), 400

        if not data.get("email"):
            return jsonify({"message": "email is required"}), 400

        lead_master_campaign = _resolve_campaign_for_request(requested_campaign_id)
        if not lead_master_campaign:
            return jsonify({"success": False, "message": "Campaign not found"}), 404

        # Ensure we have a valid Instantly campaign id.
        campaign_options = lead_master_campaign.options_settings if isinstance(lead_master_campaign.options_settings, dict) else {}
        instantly_campaign_id = str(campaign_options.get("instantly_campaign_id") or "").strip()
        if not instantly_campaign_id:
            campaign_id_text = str(lead_master_campaign.campaign_id or "").strip()
            if campaign_id_text and not _looks_like_uuid(campaign_id_text):
                instantly_campaign_id = campaign_id_text
        try:
            if not instantly_campaign_id:
                instantly_response = create_instantly_campaign(
                    campaign_name=lead_master_campaign.campaign_name,
                    schedules=lead_master_campaign.campaign_schedule or {},
                    options_settings=lead_master_campaign.options_settings or {},
                )
                new_instantly_campaign_id = instantly_response.get("id")
                if not new_instantly_campaign_id:
                    detail = instantly_response.get("message") or instantly_response.get("error") or instantly_response.get("detail")
                    return (
                        jsonify(
                            {
                                "success": False,
                                "message": f"Failed to create campaign in Instantly. {detail}" if detail else "Failed to create campaign in Instantly. Check Instantly API key and campaign settings.",
                                "instantly_response": instantly_response,
                            }
                        ),
                        502,
                    )
                instantly_campaign_id = new_instantly_campaign_id
                updated_options = dict(campaign_options)
                updated_options["instantly_campaign_id"] = instantly_campaign_id
                update_db_campaign(campaign_id=lead_master_campaign.campaign_id, options_settings=updated_options)
        except Exception as e:
            return jsonify({"success": False, "message": f"Failed to provision Instantly campaign: {str(e)}"}), 500

        # Create the lead in our DB first (to ensure dedupe + UI visibility),
        # but store Instantly campaign id in `Leads.campaign_id`.
        new_lead = add_lead_db(
            campaign_pk=lead_master_campaign.id,
            campaign_id=instantly_campaign_id,
            email=data.get("email"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            title=data.get("title"),
            company=data.get("company"),
            conference=data.get("conference"),
            type=data.get("type"),
            linkedin=data.get("linkedin"),
            website=data.get("website"),
            lead_id=None,
            lead_status=1,
        )
        if not new_lead:
            return jsonify({"success": False, "message": "Lead with this email already exists for this campaign"}), 400

        # Now create lead in Instantly and persist the returned lead id + initial statuses.
        try:
            instantly_lead = create_lead(
                campaign_id=instantly_campaign_id,
                lead_email=new_lead.email,
                first_name=new_lead.first_name or "",
                last_name=new_lead.last_name or "",
            )
            instantly_lead_id = _extract_instantly_lead_id(instantly_lead)
            if instantly_lead_id:
                update_lead(
                    db_id=new_lead.id,
                    lead_id=instantly_lead_id,
                    lead_status=1,
                    email_status="NOT Yet Contacted",
                )
                return (
                    jsonify(
                        {
                            "success": True,
                            "message": "Lead created successfully",
                            "data": {"id": new_lead.id, "lead_id": instantly_lead_id, "campaign_id": instantly_campaign_id},
                        }
                    ),
                    201,
                )
            # If Instantly didn't return an id, mark as processing/error for visibility.
            update_lead(db_id=new_lead.id, lead_status=0, email_status="PROCESSING")
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Lead saved locally but Instantly lead creation failed.",
                        "instantly_response": instantly_lead,
                    }
                ),
                502,
            )
        except Exception as e:
            update_lead(db_id=new_lead.id, lead_status=0, email_status="PROCESSING")
            return jsonify({"success": False, "message": f"Lead saved locally but Instantly call failed: {str(e)}"}), 502

    except Exception as e:
        print(e)
        return jsonify({"message": f"Error creating lead: {str(e)}"}), 500


@lead.route("/api/lead/list/", methods=["GET"])
@token_required
def lead_list(current_user):
    try:
        all_leads = get_all_leads()

        leads_list = []
        for lead in all_leads:
            lead = _ensure_external_lead_id(lead)
            lead_parent_campaign = get_campaign_db_id(lead.campaign_pk)
            lead_data = {
                "id": lead.id,
                "campaign_pk": lead.campaign_pk,
                "lead_id": lead.lead_id,
                "first_name": lead.first_name,
                "last_name": lead.last_name,
                "full_name": f"{lead.first_name} {lead.last_name}".strip(),
                "title": lead.title,
                "company": lead.company,
                "conference": lead.conference,
                "type": lead.type,
                "email": lead.email,
                "linkedin": lead.linkedin,
                "website": lead.website,
                "campaign_id": lead.campaign_id,
                "lead_status": lead.lead_status,
                "lead_processed_date": lead.lead_processed_date.isoformat() if lead.lead_processed_date else None,
                "email_status": lead.email_status,
                "email_id": lead.email_id,
                "next_reply_date": lead.next_reply_date.isoformat() if lead.next_reply_date else None,
                "reply_mail": lead.reply_mail,
                "website_data": lead.website_data,
                "linkedin_data": lead.linkedin_data,
                "generated_mail": lead.generated_mail,
                "campaign_name": lead_parent_campaign.campaign_name,
            }
            leads_list.append(lead_data)

        return jsonify({"success": True, "count": len(leads_list), "data": leads_list}), 200

    except Exception as e:
        print(e)
        return jsonify({"success": False, "error": f"Error fetching leads: {str(e)}"}), 500


@lead.route("/api/lead/details/", methods=["POST"])
@token_required
def lead_details(current_user):
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"message": "Missing JSON data"}), 400

        lead_id = data.get("lead_id")
        db_id = data.get("db_id", data.get("id"))
        if isinstance(lead_id, str):
            lead_id = lead_id.strip()
        if isinstance(db_id, str):
            db_id = db_id.strip()
            db_id = int(db_id) if db_id.isdigit() else None
        elif isinstance(db_id, (int, float)):
            db_id = int(db_id)
        else:
            db_id = None

        print("Request Lead ID: ", lead_id)
        print("Request DB ID: ", db_id)
        print()
        if not lead_id and db_id is None:
            return jsonify({"message": "lead_id or db_id is required"}), 400

        lead = None
        if lead_id:
            lead = get_lead_by_lead_id(lead_id)
            # If caller passed numeric db id in lead_id, support that too.
            if not lead and isinstance(lead_id, str) and lead_id.isdigit():
                lead = get_lead_by_db_id(int(lead_id))
        if not lead and db_id is not None:
            lead = get_lead_by_db_id(db_id)
        if not lead:
            return jsonify({"success": False, "message": "Lead not found"}), 404
        lead = _ensure_external_lead_id(lead)
        lead_parent_campaign = get_campaign_db_id(lead.campaign_pk)
        if not lead_parent_campaign:
            return jsonify({"success": False, "message": "Parent campaign not found"}), 404

        lead_data = {
            "id": lead.id,
            "lead_id": lead.lead_id,
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "full_name": f"{lead.first_name} {lead.last_name}".strip(),
            "title": lead.title,
            "company": lead.company,
            "conference": lead.conference,
            "type": lead.type,
            "email": lead.email,
            "linkedin": lead.linkedin,
            "website": lead.website,
            "campaign_id": lead.campaign_id,
            "lead_status": lead.lead_status,
            "lead_processed_date": lead.lead_processed_date.isoformat() if lead.lead_processed_date else None,
            "email_status": lead.email_status,
            "email_id": lead.email_id,
            "next_reply_date": lead.next_reply_date.isoformat() if lead.next_reply_date else None,
            "reply_mail": lead.reply_mail,
            "website_data": lead.website_data,
            "linkedin_data": lead.linkedin_data,
            "generated_mail": lead.generated_mail,
            "campaign_name": lead_parent_campaign.campaign_name,
            "campaign_status": f"{lead_parent_campaign.campaign_status}",
            "campaign_type": lead.campaign_type,
        }
        return jsonify(lead_data), 200

    except Exception as e:
        print(e)
        return jsonify({"success": False, "message": f"Error fetching lead details: {str(e)}"}), 500


@lead.route("/api/lead/update/", methods=["PUT"])
@token_required
def lead_update(current_user):
    try:
        data = request.get_json()
        print(data)
        if data is None:
            return jsonify({"message": "Missing JSON data"}), 400

        lead_id = data.get("lead_id")
        if not lead_id:
            return jsonify({"message": "lead_id is required"}), 400

        lead = get_lead_by_lead_id(lead_id)
        if not lead:
            return jsonify({"message": "Lead not found"}), 404
        update_lead(
            lead_id=lead_id,
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            title=data.get("title"),
            company=data.get("company"),
            conference=data.get("conference"),
            type=data.get("type"),
            # email=data.get("email"),
            linkedin=data.get("linkedin"),
            website=data.get("website"),
        )
        update_instantly_lead(
            lead_id=lead_id,
            lead_email=data.get("email"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
        )

        updated_lead = {
            "id": lead.id,
            "lead_id": lead.lead_id,
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "full_name": f"{lead.first_name} {lead.last_name}".strip(),
            "title": lead.title,
            "company": lead.company,
            "conference": lead.conference,
            "type": lead.type,
            "email": lead.email,
            "linkedin": lead.linkedin,
            "website": lead.website,
            "campaign_id": lead.campaign_id,
            "lead_status": lead.lead_status,
            "email_status": lead.email_status,
            "email_id": lead.email_id,
            "reply_mail": lead.reply_mail,
        }

        return jsonify({"success": True, "message": "Lead updated successfully", "data": updated_lead}), 200

    except Exception as e:
        print(e)
        return jsonify({"success": False, "message": f"Error updating lead: {str(e)}"}), 500


@lead.route("/api/lead/delete/", methods=["DELETE"])
@token_required
def lead_delete(current_user):
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"message": "Missing JSON data"}), 400

        lead_id = data.get("lead_id")
        db_id = data.get("db_id", data.get("id"))
        if isinstance(lead_id, str):
            lead_id = lead_id.strip() or None
        if isinstance(db_id, str):
            db_id = db_id.strip()
            db_id = int(db_id) if db_id.isdigit() else None
        if not lead_id and db_id is None:
            return jsonify({"message": "lead_id or db_id is required"}), 400

        # Resolve lead robustly from either external lead_id or DB id.
        db_lead = None
        if lead_id:
            db_lead = get_lead_by_lead_id(lead_id)
        if db_lead is None and db_id is not None:
            db_lead = get_lead_by_db_id(db_id)
        if not db_lead:
            return jsonify({"success": False, "message": "Lead not found"}), 404

        # Delete the lead in Instantly when we have an external lead id.
        if db_lead.lead_id:
            try:
                instantly_response = delete_lead(db_lead.lead_id)
                print("Instantly lead delete response:", instantly_response)
            except Exception as e:
                # Do not block DB cleanup on third-party failures.
                print("Instantly lead delete failed:", str(e))

        lead = delete_lead_by_lead_id(db_lead.lead_id) if db_lead.lead_id else delete_lead_by_db_id(db_lead.id)
        if not lead:
            return jsonify({"success": False, "message": "Lead not found"}), 404
        deleted_ref = db_lead.lead_id or db_lead.id
        return jsonify({"success": True, "message": f"Lead {deleted_ref} deleted successfully"}), 200

    except Exception as e:
        # db.session.rollback()
        return jsonify({"success": False, "message": f"Error deleting lead: {str(e)}"}), 500
