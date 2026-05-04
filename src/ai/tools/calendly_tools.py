from datetime import datetime, timedelta, timezone
import pickle
from zoneinfo import ZoneInfo
import requests
from langchain_core.tools import tool
from src.config.configer import Configer

configer = Configer()

CALENDLY_API_KEY = configer.get_calendly_api_key()
headers = {"Authorization": f"Bearer {CALENDLY_API_KEY}"}
ROOT_URL = "https://api.calendly.com"


# Event Checker Tool
def get_all_events_uri() -> list:
    """All all events uri data of a target event

    Returns:
        list: event uri id list
    """
    base_params = {"user": "https://api.calendly.com/users/d8a7bafe-4977-4deb-83fc-7993bf8dd0aa", "status": "active", "count": 100}

    all_events_uri = []
    next_page_token = None
    while True:
        params = base_params.copy()
        if next_page_token:
            params["page_token"] = next_page_token

        response = requests.get(f"{ROOT_URL}/scheduled_events", headers=headers, params=params)
        data = response.json()
        for event in data.get("collection", []):
            uri = event.get("uri")
            if uri:
                event_uri = uri.split("/")[-1]
                all_events_uri.append(event_uri)
        next_page_token = data.get("pagination", {}).get("next_page_token")
        if not next_page_token:
            break

    print(f"Total Events Collected: {len(all_events_uri)}")
    return all_events_uri


def process_events() -> list:
    """Process all events. Delete from pkl file if no longer available on the schedule list.
    Add if it new.

    Returns:
        list: final dict list of events {uri, email}
    """
    all_events_uri = get_all_events_uri()
    with open("src/database/calendly_events_data.pkl", "rb") as f:
        loaded_calendly_data = pickle.load(f)

    # Delete event data that not available any more
    loaded_calendly_data = [e for e in loaded_calendly_data if e["uri"] in all_events_uri]

    # Add new events not yet loaded
    for api_event_uri in all_events_uri:
        if api_event_uri not in [e["uri"] for e in loaded_calendly_data]:
            print("New Event Found: ", api_event_uri)
            response = requests.get(f"https://api.calendly.com/scheduled_events/{api_event_uri}/invitees", headers=headers)
            data = response.json()
            loaded_calendly_data.append({"uri": api_event_uri, "email": data["collection"][0]["email"]})

    with open("src/database/calendly_events_data.pkl", "wb") as f:
        pickle.dump(loaded_calendly_data, f)

    return loaded_calendly_data


@tool
def check_calendly_event_tool(email: str) -> str:
    """Check is there any schedule have with this email or not.

    Args:
        email (str): client email

    Returns:
        str: final comment
    """
    print("-------Calendly Checker Tool Called-------")
    calendly_data = process_events()  # {uri, email}
    # Check email found on this list or not.
    event_emails = [event_data["email"] for event_data in calendly_data]
    if email in event_emails:
        return "True. Email found on the schedule list."
    else:
        return "False. Email NOT found on the schedule list."


# Available time checker tool
@tool
def available_meeting_dt_checker_tool(client_date_time: str, client_time_zone: str) -> tuple:
    """
    Convert a client's local datetime to UTC and check available meeting slots.

    Args:
        client_date_time (str): Client's local datetime in the format "%m/%d/%y %I:%M:%p".
            Example: "10/30/25 09:30:PM".
        client_time_zone (str): Client's IANA timezone, e.g. "Asia/Dhaka" or "America/New_York".

     Returns:
        (bool, tuple): True if the converted UTC time matches an available host slot, otherwise False. and message
    """
    print("-------Available Meeting Date-Time Checker Tool Called-------")
    try:
        client_dt_obj = datetime.strptime(client_date_time, "%m/%d/%y %I:%M:%p")
        client_dt_with_tz = client_dt_obj.replace(tzinfo=ZoneInfo(client_time_zone))
        client_dt_utc = client_dt_with_tz.astimezone(timezone.utc)
        client_dt_utc_iso = client_dt_utc.isoformat().replace("+00:00", "Z")
    except Exception as e:
        print(e)
        return False, "Invalid Date time or Time-zone data"

    print("Client DT UTC ISO: ", client_dt_utc_iso)
    # Subtract and add 1 hour to get more slot
    start_time = client_dt_utc + timedelta(hours=-1)
    end_time = client_dt_utc + timedelta(hours=1)

    base_params = {
        "event_type": "https://api.calendly.com/event_types/709670ee-3838-431d-8c6c-88ee1482b64d",
        "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end_time": end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    response = requests.get(f"{ROOT_URL}/event_type_available_times", headers=headers, params=base_params)
    host_time_zones = [item["start_time"] for item in response.json()["collection"]]

    if client_dt_utc_iso in host_time_zones:
        return True, host_time_zones
    else:
        return False, "No slot available with this date time."


@tool
def booking_schedule_tool(
    full_name: str, email: str, time_zone: str, start_time: str, meeting_location: str = "google_conference"
) -> str:
    """Book a Calendly meeting with the client.

    Args:
        full_name: Client's full name (e.g., "John Doe")
        email: Client's email address (e.g., "john@example.com")
        time_zone: Client's IANA timezone (e.g., "Asia/Dhaka", "America/New_York")
        start_time: Meeting start time in client's timezone, format: "%m/%d/%y %I:%M:%p" (e.g., "10/30/25 09:30:PM")
        meeting_location: Meeting platform - use "google_conference" for Google Meet

    Returns:
        str: Booking status message - success confirmation or error details
    """
    print("-------Booking  Scheduler Tool Called-------")
    try:
        client_dt_obj = datetime.strptime(start_time, "%m/%d/%y %I:%M:%p")
        client_dt_with_tz = client_dt_obj.replace(tzinfo=ZoneInfo(time_zone))
        client_dt_utc = client_dt_with_tz.astimezone(timezone.utc)
        client_dt_utc_iso = client_dt_utc.isoformat().replace("+00:00", "Z")
    except Exception as e:
        print(e)
        return "Invalid Date time"

    payload = {
        "event_type": "https://api.calendly.com/event_types/709670ee-3838-431d-8c6c-88ee1482b64d",
        "start_time": client_dt_utc_iso,
        "invitee": {"name": full_name, "email": email, "timezone": time_zone},
        "location": {"kind": meeting_location},
        "questions_and_answers": [
            {"position": 0, "question": "Phone Number", "answer": "+1 212 000 0000"},
            {
                "position": 1,
                "question": "What’s the primary goal of this meeting and any specific topics you’d like to discuss?",
                "answer": "Discuss performance marketing goals and collaboration ideas.",
            },
        ],
    }
    response = requests.post(f"{ROOT_URL}/invitees", headers=headers, json=payload)
    if "resource" in response.json().keys():
        return "Booking Successful"
    else:
        return "Booking Failed. " + str(response.json())
