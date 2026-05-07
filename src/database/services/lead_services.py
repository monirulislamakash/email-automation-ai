from typing import List, Optional

from sqlalchemy.exc import IntegrityError

from src.database.session import get_session
from src.database.models.leads import Leads
from src.database.models.campaigns import Campaigns


def add_lead_db(
    campaign_pk: int,
    campaign_id: str,
    email: str,
    first_name: str,
    last_name: str,
    title: Optional[str] = None,
    company: Optional[str] = None,
    conference: Optional[str] = None,
    type: Optional[str] = None,
    linkedin: Optional[str] = None,
    website: Optional[str] = None,
    lead_id: Optional[str] = None,
    lead_status: Optional[int] = None,
) -> Optional[Leads]:
    """Create a new lead for a campaign.

    Checks for an existing lead with the same campaign and email to avoid
    duplicates.
    """
    with get_session() as session:
        existing = session.query(Leads).filter_by(campaign_id=campaign_id, email=email).first()
        if existing:
            print(f"Lead with email '{email}' already exists in campaign '{campaign_id}'.")
            return None

        new_lead = Leads(
            campaign_pk=campaign_pk,
            campaign_id=campaign_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            title=title,
            company=company,
            conference=conference,
            type=type,
            linkedin=linkedin,
            website=website,
            lead_id=lead_id,
            lead_status=lead_status,
        )
        try:
            session.add(new_lead)
            session.commit()
            print(f"New lead {first_name} {last_name} <{email}> added.")
            session.refresh(new_lead)
            return new_lead
        except IntegrityError as e:
            session.rollback()
            print("An error occurred while adding lead:", e)
            return None


def get_all_leads() -> List[Leads]:
    with get_session() as session:
        leads = session.query(Leads).all()
        return leads or []


def get_lead_by_db_id(id: str) -> Optional[Leads]:
    """Fetch a single lead using the external lead_id."""
    with get_session() as session:
        lead = session.query(Leads).filter_by(id=id).first()
        if lead:
            return lead
        else:
            print("Lead not found.")
            return None


def get_lead_by_lead_id(lead_id: str) -> Optional[Leads]:
    """Fetch a single lead using the external lead_id."""
    with get_session() as session:
        lead = session.query(Leads).filter_by(lead_id=lead_id).first()
        if lead:
            return lead
        else:
            print("Lead not found.")
            return None


def get_leads_by_campaign(campaign_id: str) -> Leads:
    """Return all leads for a campaign."""
    with get_session() as session:
        lead = session.query(Leads).filter_by(campaign_id=campaign_id).first()
        return lead
    return None


def get_master_campaign_by_instantly_campaign_id(instantly_campaign_id: str) -> Optional[Campaigns]:
    """Resolve an Instantly campaign id back to the master DB campaign.

    This supports frontend flows that accidentally reuse a returned Instantly campaign id
    as the next request's campaign_id during multi-lead uploads.
    """
    instantly_campaign_id = str(instantly_campaign_id or "").strip()
    if not instantly_campaign_id:
        return None

    with get_session() as session:
        lead = (
            session.query(Leads)
            .filter_by(campaign_id=instantly_campaign_id)
            .order_by(Leads.id.desc())
            .first()
        )
        if not lead:
            return None

        campaign = session.query(Campaigns).filter_by(id=lead.campaign_pk).first()
        return campaign


def change_lead_id(id: int, new_lead_id: str, new_campaign_id: str):
    with get_session() as session:
        lead = session.query(Leads).filter_by(id=id).first()
        if lead:
            lead.lead_id = new_lead_id
            lead.campaign_id = new_campaign_id
            session.commit()
            return True
        else:
            print("lead not found to update")
            return False


def update_lead(
    *,
    lead_id: Optional[str] = None,
    db_id: Optional[int] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    title: Optional[str] = None,
    company: Optional[str] = None,
    conference: Optional[str] = None,
    type: Optional[str] = None,
    email: Optional[str] = None,
    linkedin: Optional[str] = None,
    website: Optional[str] = None,
    website_data: Optional[str] = None,
    linkedin_data: Optional[str] = None,
    generated_mail: Optional[str] = None,
    campaign_id: Optional[str] = None,
    campaign_type: Optional[str] = None,
    lead_status: Optional[int] = None,
    lead_processed_date=None,
    email_status: Optional[str] = None,
    email_id: Optional[str] = None,
    next_reply_date: Optional[str] = None,
    reply_mail: Optional[str] = None,
) -> bool:
    """Update a lead. Locate by lead_id or db_id.

    Only non-None fields are updated.
    """
    with get_session() as session:
        lead = None
        if lead_id:
            lead = session.query(Leads).filter_by(lead_id=lead_id).first()
        if lead is None and db_id is not None:
            lead = session.query(Leads).filter_by(id=db_id).first()

        if not lead:
            print("Lead not found to update.")
            return False

        try:
            if first_name is not None:
                lead.first_name = first_name
            if last_name is not None:
                lead.last_name = last_name
            if title is not None:
                lead.title = title
            if company is not None:
                lead.company = company
            if conference is not None:
                lead.conference = conference
            if type is not None:
                lead.type = type
            if email is not None:
                lead.email = email
            if linkedin is not None:
                lead.linkedin = linkedin
            if website is not None:
                lead.website = website
            if website_data is not None:
                lead.website_data = website_data
            if linkedin_data is not None:
                lead.linkedin_data = linkedin_data
            if generated_mail is not None:
                lead.generated_mail = generated_mail
            if campaign_id is not None:
                lead.campaign_id = campaign_id
            if campaign_type is not None:
                lead.campaign_type = campaign_type
            if lead_status is not None:
                lead.lead_status = lead_status
            if lead_processed_date is not None:
                lead.lead_processed_date = lead_processed_date
            if email_status is not None:
                lead.email_status = email_status
            if email_id is not None:
                lead.email_id = email_id
            if next_reply_date is not None:
                lead.next_reply_date = next_reply_date
            if reply_mail is not None:
                lead.reply_mail = reply_mail

            session.commit()
            print("Lead updated successfully.")
            return True
        except IntegrityError as e:
            session.rollback()
            print("An error occurred while updating lead:", e)
            return False


def update_lead_null(lead_id: str):
    with get_session() as session:
        lead = session.query(Leads).filter_by(lead_id=lead_id).first()
        if lead:
            lead.next_reply_date = None
            lead.reply_mail = None
            session.commit()
            print("Lead updated successfully.")
            return True
        else:
            print("Lead not found to update.")
            return False


def delete_lead_by_db_id(db_id: int) -> bool:
    """Delete a lead using the database primary key id."""
    with get_session() as session:
        lead = session.query(Leads).filter_by(id=db_id).first()
        if lead:
            session.delete(lead)
            session.commit()
            return True
        else:
            print("Lead not found to delete.")
            return False


def delete_lead_by_lead_id(lead_id: str) -> bool:
    """Delete a lead using the external lead_id."""
    with get_session() as session:
        lead = session.query(Leads).filter_by(lead_id=lead_id).first()
        if lead:
            session.delete(lead)
            session.commit()
            return True
        else:
            print("Lead not found to delete.")
            return False
