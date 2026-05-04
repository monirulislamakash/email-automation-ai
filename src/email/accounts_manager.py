import requests
from src.config.configer import Configer

configer = Configer()

API_KEY = configer.get_instantly_api_key()
ROOT_URL = "https://api.instantly.ai/api/v2/accounts"


def get_email_accounts() -> list:
    """Get active email accounts

    Returns:
        str: List of active email list
    """
    url = f"{ROOT_URL}?status=1&limit=30"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    response = requests.get(url, headers=headers)
    data = response.json()
    email_accounts = []
    for email_account in data["items"]:
        email_accounts.append(email_account["email"])
    return email_accounts


def get_email_account_details(email: str) -> list:
    """Get a target email account details

    Returns:
        str: email addr
    """
    url = f"{ROOT_URL}/{email}"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    response = requests.get(url, headers=headers)
    data = response.json()
    full_name = data["first_name"] + " " + data["last_name"]
    return full_name
