import requests
from src.config.configer import Configer

configer = Configer()

API_KEY = configer.get_instantly_api_key()
ROOT_URL = "https://api.instantly.ai/api/v2/leads"


def create_lead(campaign_id: str, lead_email: str, first_name: str, last_name: str) -> dict:
    """Add a lead to a specified campaign
    Args:
        campaign_id (str): Selected Campaign ID
        lead_email (str): Lead Email Address
        first_name (str): First Name
        last_name (str): Last Name

    Returns:
        dict: Response Data
    """
    url = ROOT_URL

    payload = {
        "campaign": campaign_id,
        "email": lead_email,
        "first_name": first_name,
        "last_name": last_name,
    }

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers)
    return response.json()


def update_instantly_lead(lead_id: str, lead_email: str, first_name: str, last_name: str) -> dict:
    """update a lead to a specified campaign
    Args:
        lead_email (str): Lead Email Address
        first_name (str): First Name
        last_name (str): Last Name

    Returns:
        dict: Response Data
    """
    url = ROOT_URL + "/" + lead_id

    payload = {
        "email": lead_email,
        "first_name": first_name,
        "last_name": last_name,
        "company_domain": lead_email,
    }

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    response = requests.patch(url, json=payload, headers=headers)
    print(response.json())
    return response.json()


def get_lead_info(lead_id: str) -> dict:
    url = f"{ROOT_URL}/{lead_id}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    response = requests.get(url, headers=headers)
    data = response.json()
    return data


def delete_lead(lead_id: str) -> dict:
    """Delete a specified lead

    Args:
        lead_id (str): Selected Lead ID

    Returns:
        dict: Response Data
    """
    url = f"{ROOT_URL}/{lead_id}"

    headers = {"Authorization": f"Bearer {API_KEY}"}

    response = requests.delete(url, headers=headers)
    data = response.json()
    # print(data)
    return data
