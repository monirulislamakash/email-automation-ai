import bs4
import requests
from src.config.configer import Configer

configer = Configer()

API_KEY = configer.get_instantly_api_key()
ROOT_URL = "https://api.instantly.ai/api/v2/emails"


def get_email_id(campaign_id: str) -> str:
    """Get email uuid

    Args:
        campaign_id (str): Target Lead Campaign ID

    Returns:
        str: Email uuid
    """
    url = f"{ROOT_URL}?campaign_id={campaign_id}"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    response = requests.get(url, headers=headers)
    data = response.json()["items"][0].get("id")
    return data


def get_full_conversation(campaign_id: str) -> str:
    """Get full conversation of a target lead

    Args:
        campaign_id (str): Target Lead Campaign ID

    Returns:
        str: Full email conversation as string
    """
    url = f"{ROOT_URL}"
    params = {
        'campaign_id': campaign_id
    }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    resp = requests.get(url, headers=headers, params=params)
    emails = list(resp.json()["items"])
    emails.reverse()
    full_conversation = ""
    for email in emails:

        full_conversation += "\nFrom: " + email["from_address_email"] + "\n"
        full_conversation += "Subject: " + email["subject"] + "\n"
        full_conversation += "Body: " + bs4.BeautifulSoup(email["body"]["html"], "html.parser").text + "\n" 
        full_conversation += "=" * 50
    return full_conversation


def send_reply(sender_email: str, reply_uuid: str, body: dict) -> dict:
    """Reply to a targer mail

    Args:
        sender_email (str): Sender eaccount email
        reply_uuid (str): Targer conversation id
        body (dict): Body message in dictionary format

    Returns:
        dict: Response data
    """
    # get subject dynamically
    headers = {"Authorization": f"Bearer {API_KEY}"}
    url = f"{ROOT_URL}/{reply_uuid}"
    subject = requests.get(url, headers=headers).json().get("subject")

    # send reply
    url = f"{ROOT_URL}/reply"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    payload = {
        "eaccount": sender_email,
        "reply_to_uuid": reply_uuid,
        "subject": subject,
        "body": body,
    }

    response = requests.post(url, json=payload, headers=headers)
    data = response.json()
    return data
