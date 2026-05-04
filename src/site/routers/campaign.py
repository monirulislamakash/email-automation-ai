import uuid
from flask import Blueprint, jsonify, request
from src.site.routers.auth import token_required
from src.database.services.campaign_services import (
    add_campaign,
    get_all_campaigns,
    update_db_campaign,
    delete_db_campaign,
    get_campaign,
    get_campaign_db_id,
    get_campaign_leads,
)
from src.email.campaign_manager import (
    create_campaign,
    activate_campaign,
    delete_campaign,
    update_campaign,
    get_campaign as get_instantly_campaign,
    find_campaign_by_name,
)

campaign = Blueprint("campaign", __name__)


def _to_number(value):
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _looks_like_uuid(value):
    text = str(value or "").strip()
    return len(text) == 36 and text.count("-") == 4


def _pick_nested(data, keys):
    for key in keys:
        if isinstance(data, dict) and key in data and data[key] is not None:
            return data[key]
    return None


def _resolve_instantly_campaign_id(primary_campaign_id, leads, options_settings=None, campaign_name=None):
    options = options_settings if isinstance(options_settings, dict) else {}
    option_instantly_id = str(options.get("instantly_campaign_id") or "").strip()
    if option_instantly_id and not _looks_like_uuid(option_instantly_id):
        return option_instantly_id

    primary = str(primary_campaign_id or "").strip()
    if primary and not _looks_like_uuid(primary):
        return primary

    candidates = []
    for lead in leads or []:
        lead_campaign_id = str(getattr(lead, "campaign_id", "") or "").strip()
        if lead_campaign_id:
            candidates.append(lead_campaign_id)

    for candidate in candidates:
        if not _looks_like_uuid(candidate):
            return candidate

    try:
        match = find_campaign_by_name(campaign_name)
        if isinstance(match, dict):
            found_id = str(match.get("id") or "").strip()
            if found_id and not _looks_like_uuid(found_id):
                return found_id
    except Exception as lookup_error:
        print(f"Warning: failed to resolve Instantly campaign id by name '{campaign_name}': {lookup_error}")

    return None


def _extract_live_campaign_stats(payload):
    if not isinstance(payload, dict):
        return {}

    stats_root = payload.get("stats") if isinstance(payload.get("stats"), dict) else {}
    analytics_root = payload.get("analytics") if isinstance(payload.get("analytics"), dict) else {}

    sent_value = _pick_nested(
        payload,
        ["emails_sent", "emails_sent_count", "sent", "sent_count", "emailsSent", "sentCount"],
    )
    if sent_value is None:
        sent_value = _pick_nested(stats_root, ["emails_sent", "emails_sent_count", "sent", "sent_count"])
    if sent_value is None:
        sent_value = _pick_nested(analytics_root, ["emails_sent", "emails_sent_count", "sent", "sent_count"])

    opened_value = _pick_nested(payload, ["opened", "opened_count", "opens", "open_count"])
    if opened_value is None:
        opened_value = _pick_nested(stats_root, ["opened", "opened_count", "opens", "open_count"])
    if opened_value is None:
        opened_value = _pick_nested(analytics_root, ["opened", "opened_count", "opens", "open_count"])

    replied_value = _pick_nested(payload, ["replied", "replied_count", "replies", "reply_count"])
    if replied_value is None:
        replied_value = _pick_nested(stats_root, ["replied", "replied_count", "replies", "reply_count"])
    if replied_value is None:
        replied_value = _pick_nested(analytics_root, ["replied", "replied_count", "replies", "reply_count"])

    progress_value = _pick_nested(payload, ["progress", "progress_percent", "completed_percentage", "completion_rate"])
    if progress_value is None:
        progress_value = _pick_nested(stats_root, ["progress", "progress_percent", "completed_percentage", "completion_rate"])
    if progress_value is None:
        progress_value = _pick_nested(analytics_root, ["progress", "progress_percent", "completed_percentage", "completion_rate"])

    total_leads = _pick_nested(payload, ["total_leads", "leads_count", "lead_count"])
    if total_leads is None:
        total_leads = _pick_nested(stats_root, ["total_leads", "leads_count", "lead_count"])
    if total_leads is None:
        total_leads = _pick_nested(analytics_root, ["total_leads", "leads_count", "lead_count"])

    sent_number = _to_number(sent_value)
    progress_number = _to_number(progress_value)
    total_number = _to_number(total_leads)
    if progress_number is None and sent_number is not None and total_number and total_number > 0:
        progress_number = (sent_number / total_number) * 100

    opened_number = _to_number(opened_value)
    replied_number = _to_number(replied_value)

    return {
        "progress": progress_number,
        "sent": sent_number,
        "opened": opened_number,
        "replied": replied_number,
        "status": _pick_nested(payload, ["status", "status_text", "state", "campaign_state"]),
        "campaign_status": _pick_nested(payload, ["campaign_status", "status_code", "state_code"]),
    }


def _is_completed_status(value):
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {"3", "completed", "complete"}


def get_campaign_stats(id: str, campaign_external_id: str = None, options_settings=None, campaign_name=None):
    leads = get_campaign_leads(id) or []
    total_leads = len(leads)
    sent = 0
    opened = 0
    replied = 0
    for lead in leads:
        if lead.lead_status != 1 and lead.lead_status != 2:
            sent += 1
        if lead.email_status == "Email Opened":
            opened += 1
        if lead.email_status == "Email Replied":
            replied += 1
    progress = (sent / total_leads) * 100 if total_leads > 0 else 0
    stats = {"progress": progress, "sent": sent, "opened": opened, "replied": replied}

    instantly_campaign_id = _resolve_instantly_campaign_id(
        campaign_external_id,
        leads,
        options_settings=options_settings,
        campaign_name=campaign_name,
    )

    if instantly_campaign_id:
        try:
            live_campaign = get_instantly_campaign(instantly_campaign_id)
            live_stats = _extract_live_campaign_stats(live_campaign)
            for key, value in live_stats.items():
                if value is not None:
                    if key == "progress":
                        stats[key] = float(value)
                    elif key in {"sent", "opened", "replied"}:
                        stats[key] = int(float(value))
                    else:
                        stats[key] = value
        except Exception as instant_error:
            print(f"Warning: failed to fetch live campaign stats for {instantly_campaign_id}: {instant_error}")

    # When a campaign is completed (status code 3), sent/progress should reflect completion
    # even if event/webhook counters are delayed or unavailable.
    status_marker = stats.get("status")
    campaign_status_marker = stats.get("campaign_status")
    if _is_completed_status(status_marker) or _is_completed_status(campaign_status_marker):
        if total_leads > 0:
            stats["sent"] = max(int(stats.get("sent", 0) or 0), total_leads)
            stats["progress"] = 100.0

    return stats


@campaign.route("/api/add/campaign/", methods=["POST"], strict_slashes=False)
@token_required
def campaign_create(current_user):
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"message": "Missing JSON data"}), 400

        if not data.get("campaign_name"):
            return jsonify({"message": "campaign_name is required"}), 400

        campaign_name = data.get("campaign_name")
        campaign_schedule = data.get("campaign_schedule")
        if campaign_schedule is None and data.get("schedules") is not None:
            campaign_schedule = {"schedules": data.get("schedules")}
        options_settings = data.get("options_settings")

        new_campaign = add_campaign(
            campaign_name=campaign_name,
            campaign_id=str(uuid.uuid4()),
            campaign_schedule=campaign_schedule,
            options_settings=options_settings,
        )

        campaign_data = {
            "id": new_campaign.id,
            "campaign_id": new_campaign.campaign_id,
            "campaign_name": new_campaign.campaign_name,
            "campaign_type": "",
            "campaign_schedule": new_campaign.campaign_schedule,
            "options_settings": new_campaign.options_settings,
            "status": new_campaign.status,
            "campaign_status": new_campaign.campaign_status,
        }

        return jsonify({"success": True, "message": "Campaign created successfully", "data": campaign_data}), 201

    except Exception as e:
        print(e)
        return jsonify({"success": False, "message": f"Error creating campaign: {str(e)}"}), 500


@campaign.route("/api/campaign/details/", methods=["POST"])
@token_required
def campaign_details(current_user):
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"message": "Missing JSON data"}), 400

        campaign_id = data.get("campaign_id")
        print("Request Campaign ID: ", campaign_id)
        if not campaign_id:
            return jsonify({"message": "campaign_id is required"}), 400

        campaign = get_campaign(campaign_id)
        if not campaign:
            return jsonify({"success": False, "message": "Campaign not found"}), 404

        campaign_data = {
            "id": campaign.id,
            "campaign_id": campaign.campaign_id,
            "campaign_name": campaign.campaign_name,
            "campaign_type": "",
            "campaign_status": str(campaign.campaign_status),
            "campaign_schedule": campaign.campaign_schedule,
            "options_settings": campaign.options_settings,
            "status": campaign.status,
            "stats": get_campaign_stats(
                campaign.id,
                campaign.campaign_id,
                options_settings=campaign.options_settings,
                campaign_name=campaign.campaign_name,
            ),
        }

        return jsonify(campaign_data), 200

    except Exception as e:
        print(e)
        return jsonify({"success": False, "message": f"Error fetching campaign details: {str(e)}"}), 500


@campaign.route("/api/campaign/list/", methods=["GET"])
@token_required
def campaign_list(current_user):
    try:
        all_campaigns = get_all_campaigns()
        if all_campaigns:
            campaigns_list = []
            for campaign in all_campaigns:
                campaign_data = {
                    "id": campaign.id,
                    "campaign_id": campaign.campaign_id,
                    "campaign_name": campaign.campaign_name,
                    "campaign_type": "",
                    "campaign_status": campaign.campaign_status,
                    "campaign_schedule": campaign.campaign_schedule,
                    "options_settings": campaign.options_settings,
                    "status": campaign.status,
                    "stats": get_campaign_stats(
                        campaign.id,
                        campaign.campaign_id,
                        options_settings=campaign.options_settings,
                        campaign_name=campaign.campaign_name,
                    ),
                }
                campaigns_list.append(campaign_data)
            print(campaigns_list[0]["stats"])
            return jsonify({"success": True, "count": len(campaigns_list), "data": campaigns_list}), 200
        else:
            campaigns_list = []
            return jsonify({"success": True, "count": 0, "data": campaigns_list}), 200

    except Exception as e:
        print(e)
        return jsonify({"success": False, "error": f"Error fetching campaigns: {str(e)}"}), 500


@campaign.route("/api/campaign/update/", methods=["PUT"])
@token_required
def campaign_update(current_user):
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"message": "Missing JSON data"}), 400
        print(data)
        campaign_id = data.get("campaign_id")
        if not campaign_id:
            return jsonify({"message": "campaign_id is required"}), 400

        tab = str(data.get("tab") or "").strip().lower()
        if not tab:
            return jsonify({"message": "tab is required"}), 400

        campaign = get_campaign(campaign_id)
        if not campaign:
            return jsonify({"message": "Campaign not found"}), 404

        if tab == "schedule":
            schedule_payload = data.get("campaign_schedule")
            if schedule_payload is None and data.get("schedules") is not None:
                schedule_payload = {"schedules": data.get("schedules")}
            if schedule_payload is None:
                return jsonify({"message": "campaign_schedule or schedules is required for tab=schedule"}), 400
            updated_campaign = update_db_campaign(campaign_id=campaign_id, campaign_schedule=schedule_payload)

        elif tab == "initiate":
            updated_campaign = update_db_campaign(
                campaign_id=campaign_id,
                campaign_name=data.get("campaign_name"),
                options_settings=data.get("options_settings"),
            )

        elif tab == "options":
            updated_campaign = update_db_campaign(
                campaign_id=campaign_id,
                campaign_name=data.get("campaign_name"),
                options_settings=data.get("options_settings"),
            )
        elif tab == "status":
            campaign_status = data.get("campaign_status")
            # Campaign mail generate korar por active hobe
            updated_campaign = update_db_campaign(campaign_id=campaign_id, campaign_status=int(campaign_status))

        else:
            return jsonify({"message": "Invalid tab name"}), 400

        if not updated_campaign:
            return jsonify({"success": False, "message": "Failed to update campaign"}), 500

        # Best-effort external sync: local DB update should still succeed.
        campaign_db_id = get_campaign(campaign_id).id
        try:
            all_campaign_leads = get_campaign_leads(campaign_db_id) or []
            for lead in all_campaign_leads:
                update_campaign(campaign_db_id=campaign_db_id, campaign_id=lead.campaign_id)
        except Exception as sync_error:
            print(f"Warning: external campaign sync failed: {sync_error}")

        updated_campaign_data = {
            "id": updated_campaign.id,
            "campaign_id": updated_campaign.campaign_id,
            "campaign_name": updated_campaign.campaign_name,
            "campaign_type": "",
            "campaign_status": updated_campaign.campaign_status,
            "campaign_schedule": updated_campaign.campaign_schedule,
            "options_settings": updated_campaign.options_settings,
            "status": updated_campaign.status,
        }

        return jsonify({"success": True, "message": "Campaign updated successfully", "data": updated_campaign_data}), 200

    except Exception as e:
        print(e)
        return jsonify({"success": False, "message": f"Error updating campaign: {str(e)}"}), 500


@campaign.route("/api/campaign/delete/", methods=["DELETE"])
@token_required
def campaign_delete(current_user):
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"message": "Missing JSON data"}), 400

        campaign_id = data.get("campaign_id")
        if not campaign_id:
            return jsonify({"message": "campaign_id is required"}), 400

        campaign_db_id = get_campaign(campaign_id).id
        all_campaign_leads = get_campaign_leads(campaign_db_id)
        for lead in all_campaign_leads:
            print("Deleting Request Campaign ID: ", lead.campaign_id)
            delete_campaign(campaign_id=lead.campaign_id)

        campaign = delete_db_campaign(campaign_id)
        if not campaign:
            return jsonify({"success": False, "message": "Campaign not found"}), 404
        return jsonify({"success": True, "message": f"Campaign {campaign_id} deleted successfully"}), 200

    except Exception as e:
        return jsonify({"success": False, "message": f"Error deleting campaign: {str(e)}"}), 500
