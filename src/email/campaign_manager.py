import json
import requests
from typing import Optional
from datetime import datetime
from src.config.configer import Configer
from src.database.services.campaign_services import get_campaign_settings

configer = Configer()

API_KEY = configer.get_instantly_api_key()
ROOT_URL = "https://api.instantly.ai/api/v2/campaigns"


def _to_24h(value: str, meridiem: Optional[str] = None) -> str:
    if not value:
        return "09:00"
    value = str(value).strip()
    if len(value) == 5 and value[2] == ":":
        return value
    parsed = None
    candidate = value
    if meridiem and meridiem.upper() in {"AM", "PM"} and meridiem.upper() not in value.upper():
        candidate = f"{value} {meridiem.upper()}"
    for fmt in ("%I:%M %p", "%H:%M"):
        try:
            parsed = datetime.strptime(candidate, fmt)
            break
        except ValueError:
            continue
    if parsed:
        return parsed.strftime("%H:%M")
    return "09:00"


def _normalize_schedule(schedule: Optional[dict]) -> dict:
    schedule = schedule or {}
    if isinstance(schedule, dict) and isinstance(schedule.get("schedules"), list):
        # Already compatible with Instantly format.
        return schedule

    day_map = {
        "sunday": "0",
        "monday": "1",
        "tuesday": "2",
        "wednesday": "3",
        "thursday": "4",
        "friday": "5",
        "saturday": "6",
    }
    selected_days = schedule.get("days") or []
    if not isinstance(selected_days, list):
        selected_days = []
    days_payload = {v: False for v in day_map.values()}
    has_any_day = False
    for day in selected_days:
        key = day_map.get(str(day).strip().lower())
        if key is not None:
            days_payload[key] = True
            has_any_day = True
    if not has_any_day:
        # Fallback to weekdays
        for key in ("1", "2", "3", "4", "5"):
            days_payload[key] = True

    from_meridiem = schedule.get("from_meridiem")
    to_meridiem = schedule.get("to_meridiem")
    start_date = None
    end_date = schedule.get("end_date")
    if isinstance(end_date, str) and end_date:
        try:
            end_date = datetime.strptime(end_date, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            # Keep as-is if it's already in API-compatible format.
            pass

    return {
        "start_date": start_date,
        "end_date": end_date,
        "schedules": [
            {
                "name": schedule.get("schedule_name") or "Default Schedule",
                "timing": {
                    "from": _to_24h(schedule.get("from_time", ""), from_meridiem),
                    "to": _to_24h(schedule.get("to_time", ""), to_meridiem),
                },
                "days": days_payload,
                "timezone": schedule.get("timezone") or "Asia/Dhaka",
            }
        ],
    }


def _normalize_options(options_settings: Optional[dict]) -> dict:
    options_settings = options_settings or {}
    if not isinstance(options_settings, dict):
        return {}

    toggles = options_settings.get("toggles") or {}
    email_list = options_settings.get("email_list") or options_settings.get("sender_emails") or []
    if not isinstance(email_list, list):
        email_list = []
    additional = options_settings.get("additional_sender_emails") or []
    if isinstance(additional, list):
        email_list = [*email_list, *additional]

    payload = {
        "email_list": email_list,
        "daily_limit": options_settings.get("daily_limit"),
        "cc_list": options_settings.get("cc_list") or options_settings.get("cc") or [],
        "bcc_list": options_settings.get("bcc_list") or options_settings.get("bcc") or [],
        "link_tracking": toggles.get("Enable link tracking"),
        "open_tracking": toggles.get("Enable open tracking"),
        "insert_unsubscribe_header": toggles.get("Include unsubscribe header"),
        "prioritize_new_leads": toggles.get("Prioritize new leads"),
        "stop_on_reply": toggles.get("Stop on reply"),
        "stop_on_auto_reply": toggles.get("Stop on auto-reply"),
        "stop_for_company": toggles.get("Stop for company"),
        "disable_bounce_protect": toggles.get("Disable bounceProtect"),
    }
    return {k: v for k, v in payload.items() if v is not None}


def create_campaign(campaign_name: str, schedules: dict, options_settings: dict) -> dict:
    """Create Campaign for A Lead

    Args:
        campaign_name (str): Campaign Name
        subject (str): Email Subject
        body (str): Email Body
        email_list (list): Sender Email List

    Returns:
        dict: Response Data
    """
    url = ROOT_URL
    payload = {"name": campaign_name, "campaign_schedule": _normalize_schedule(schedules)}
    normalized_options = _normalize_options(options_settings)
    for k, v in normalized_options.items():
        payload[k] = v

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}

    print("Creating Campaign with payload: ")
    print()
    # print(payload)
    print()
    response = requests.post(url, json=payload, headers=headers)

    data = response.json()
    # print(data)
    return data


def update_campaign(*, campaign_db_id: int, campaign_id: str, subject: Optional[str] = None, body: Optional[str] = None) -> dict:
    """Update Campaign

    Args:
        campaign_id (str): Campaign ID
        subject (str): Email Subject
        body (str): Email Body

    Returns:
        dict: Response Data
    """
    url = f"{ROOT_URL}/{campaign_id}"
    payload = {}
    if subject is not None and body is not None:
        payload["sequences"] = [
            {
                "steps": [
                    {
                        "type": "email",
                        "delay": 1,
                        "variants": [{"subject": subject, "body": body}],
                    }
                ]
            }
        ]

    campaign_data = get_campaign_settings(campaign_db_id)
    campaign_schedule = campaign_data["campaign_schedule"]
    payload["campaign_schedule"] = _normalize_schedule(campaign_schedule)
    options_settings = campaign_data["options_settings"]
    normalized_options = _normalize_options(options_settings)
    for k, v in normalized_options.items():
        payload[k] = v

    # print("Final Payload Before Update: ", payload)
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}

    response = requests.patch(url, json=payload, headers=headers)

    data = response.json()
    # print(payload)
    # print("===============")
    # print(data)
    return data


def get_campaign(campaign_id: str) -> dict:
    """Get a specified campaign data

    Args:
        campaign_id (str): Selected Campaign ID

    Returns:
        dict: Response Data
    """
    url = f"{ROOT_URL}/{campaign_id}"

    headers = {"Authorization": f"Bearer {API_KEY}"}
    response = requests.get(url, headers=headers)

    data = response.json()
    return data


def list_campaigns(limit: int = 100) -> list:
    """List campaigns from Instantly."""
    url = ROOT_URL
    headers = {"Authorization": f"Bearer {API_KEY}"}
    response = requests.get(url, params={"limit": limit}, headers=headers)
    data = response.json()
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("data", "items", "campaigns", "results"):
            if isinstance(data.get(key), list):
                return data.get(key)
    return []


def find_campaign_by_name(campaign_name: str) -> Optional[dict]:
    target = str(campaign_name or "").strip().lower()
    if not target:
        return None
    campaigns = list_campaigns(limit=200)
    for campaign in campaigns:
        name = str(campaign.get("name") or campaign.get("campaign_name") or "").strip().lower()
        if name == target:
            return campaign
    return None


def activate_campaign(campaign_id: str) -> dict:
    """Activate a specified campaign

    Args:
        campaign_id (str): Selected Campaign ID

    Returns:
        dict: Response Data
    """
    url = f"{ROOT_URL}/{campaign_id}/activate"

    headers = {"Authorization": f"Bearer {API_KEY}"}

    response = requests.post(url, headers=headers)

    data = response.json()
    return data


def delete_campaign(campaign_id: str) -> dict:
    """Delete a specified campaign

    Args:
        campaign_id (str): Selected Campaign ID

    Returns:
        dict: Response Data
    """
    url = f"{ROOT_URL}/{campaign_id}"

    headers = {"Authorization": f"Bearer {API_KEY}"}

    response = requests.delete(url, headers=headers)
    data = response.json()
    return data
