from typing import Optional, Dict

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from src.database.session import get_session
from src.database.models.campaigns import Campaigns
from src.database.models.leads import Leads
from src.database.models.prompts import CustomPrompts


def add_campaign(campaign_name: str, campaign_id: str, campaign_schedule: str, options_settings: str):
    with get_session() as session:
        new_campaign = Campaigns(
            campaign_name=campaign_name,
            campaign_id=campaign_id,
            campaign_schedule=campaign_schedule,
            options_settings=options_settings,
        )
        try:
            session.add(new_campaign)
            session.commit()
            print(f"New campaign {campaign_name} added successfully.")
            return new_campaign
        except IntegrityError as e:
            session.rollback()
            print("An error occurred:", e)
            return False


def get_all_campaigns():
    with get_session() as session:
        campaigns = session.query(Campaigns).all()
        if campaigns:
            return campaigns
        else:
            return None


def get_campaign(campaign_id: str):
    "Get campaign by campaign_id"
    with get_session() as session:
        campaign = session.query(Campaigns).filter_by(campaign_id=campaign_id).first()
        if campaign:
            return campaign
        else:
            print("Campaign not found")
            return False


def get_campaign_db_id(id: int):
    "Get campaign by campaign_id"
    with get_session() as session:
        campaign = session.query(Campaigns).filter_by(id=int(id)).first()
        if campaign:
            return campaign
        else:
            print("Campaign not found")
            return False


def delete_db_campaign(campaign_id: str):
    "Delete by DB primary key id"
    with get_session() as session:
        campaign = session.query(Campaigns).filter_by(campaign_id=campaign_id).first()
        if campaign:
            session.delete(campaign)  # delete the user
            session.commit()
            return True
        else:
            print("Campaign not found to delete")
            return False


def get_campaign_settings(campaign_db_id: str):
    with get_session() as session:
        campaign = session.query(Campaigns).filter_by(id=campaign_db_id).first()
        if campaign:
            return {"campaign_schedule": campaign.campaign_schedule, "options_settings": campaign.options_settings}
        return None


def get_campaign_senders(id: str) -> list:
    with get_session() as session:
        campaign = session.query(Campaigns).filter_by(id=id).first()
        if campaign:
            try:
                return campaign.options_settings.get("email_list")
            except AttributeError:
                return None
        return None


def get_campaign_leads(id: str) -> list:
    with get_session() as session:
        campaign = session.query(Campaigns).filter_by(id=id).first()
        if campaign:
            return campaign.leads
        return None


def change_campaign_id(id: int, new_campaign_id: str):
    with get_session() as session:
        campaign = session.query(Campaigns).filter_by(id=id).first()
        if not campaign:
            print("Campaign not found to update")
            return False

        exists = session.query(Campaigns.id).filter_by(campaign_id=new_campaign_id).first()
        if exists:
            print(f"Campaign ID '{new_campaign_id}' already exists. Choose a different id.")
            return False

        old_campaign_id = campaign.campaign_id
        if old_campaign_id == new_campaign_id:
            print("New campaign id matches existing id; nothing to update.")
            return True

        try:
            session.execute(text("PRAGMA foreign_keys=OFF"))
            campaign.campaign_id = new_campaign_id
            # Update dependent rows referencing the old campaign id.
            session.query(Leads).filter_by(campaign_id=old_campaign_id).update(
                {"campaign_id": new_campaign_id}, synchronize_session=False
            )
            session.query(CustomPrompts).filter_by(campaign_id=old_campaign_id).update(
                {"campaign_id": new_campaign_id}, synchronize_session=False
            )
            session.flush()  # push changes while FK checks are off
            session.execute(text("PRAGMA foreign_keys=ON"))
            session.commit()
            return True
        except IntegrityError as e:
            session.rollback()
            try:
                session.execute(text("PRAGMA foreign_keys=ON"))
            except Exception:
                pass
            print("Failed to update campaign id:", e)
            return False
        except Exception as e:
            session.rollback()
            try:
                session.execute(text("PRAGMA foreign_keys=ON"))
            except Exception:
                pass
            print("Unexpected error while updating campaign id:", e)
            return False


def update_db_campaign_status(id: int, status: int):
    with get_session() as session:
        campaign = session.query(Campaigns).filter_by(id=id).first()
        if campaign:
            campaign.status = status
            session.commit()
            return True
        return False


def update_db_campaign(
    *,
    campaign_id: str,
    campaign_name: Optional[str] = None,
    campaign_schedule: Optional[Dict] = None,
    options_settings: Optional[Dict] = None,
    campaign_status: Optional[int] = None,
    campaign_type: Optional[str] = None,
    status: Optional[int] = None,
):
    with get_session() as session:
        campaign = session.query(Campaigns).filter_by(campaign_id=campaign_id).first()
        if not campaign:
            print("Campaign not found to update.")
            return False

        try:
            if campaign_name is not None:
                campaign.campaign_name = campaign_name
            if campaign_schedule is not None:
                campaign.campaign_schedule = campaign_schedule
            if options_settings is not None:
                campaign.options_settings = options_settings
            if campaign_status is not None:
                campaign.campaign_status = campaign_status
            if campaign_type is not None:
                campaign.campaign_type = campaign_type
            if status is not None:
                print("Status", status)
                campaign.status = status
            session.commit()
            print("Campaign updated successfully.")
            return campaign
        except Exception as e:
            session.rollback()
            print("An error occurred while updating campaign:", e)
            return False
