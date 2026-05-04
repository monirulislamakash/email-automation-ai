import time
from json import JSONDecodeError

import requests

from src.config.configer import Configer

# Docker / slow networks: short timeouts cause ConnectTimeout on progress polling and abort the whole lead.
_DEFAULT_TIMEOUT = (60, 180)  # (connect, read) seconds
_MAX_PROGRESS_POLLS = 120
_MAX_REQUEST_RETRIES = 5

API_KEY = Configer().get_brightdata_api_key()


def _request_with_retries(session: requests.Session, method: str, url: str, **kwargs) -> requests.Response:
    kwargs.setdefault("timeout", _DEFAULT_TIMEOUT)
    last_err = None
    for attempt in range(_MAX_REQUEST_RETRIES):
        try:
            return session.request(method, url, **kwargs)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_err = e
            wait = min(2 ** attempt, 30)
            print(f"BrightData {method} {url[:60]}... retry {attempt + 1}/{_MAX_REQUEST_RETRIES}: {e} (sleep {wait}s)")
            time.sleep(wait)
    raise last_err


def get_linkedin_data(linkedin_url: str) -> dict:
    """Scrape LinkedIn data using BrightData API
    Args:
            linkedin_url: Target linkedin profile url
    Returns:
        dict: Linkedin data in dict format
    """
    if not API_KEY:
        print("BRIGHTDATA_API_KEY is missing (DB or BRIGHTDATA_API_KEY env). Skipping LinkedIn scrape.")
        return None

    session = requests.Session()
    url = "https://api.brightdata.com/datasets/v3/trigger"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    params = {
        "dataset_id": "gd_l1viktl72bvl7bjuj0",
        "include_errors": "true",
    }
    data = [{"url": linkedin_url}]

    try:
        response = _request_with_retries(session, "POST", url, headers=headers, params=params, json=data)
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
        print("BrightData trigger failed after retries:", e)
        return None

    if not response.ok:
        print(
            "BrightData trigger request failed.",
            "Status:",
            response.status_code,
            "Body:",
            response.text[:500],
        )
        return None

    try:
        trigger_payload = response.json()
    except JSONDecodeError as e:
        print("Failed to parse BrightData trigger response:", e)
        print("Raw body:", response.text[:500])
        return None

    snapshot_id = trigger_payload.get("snapshot_id")
    if not snapshot_id:
        print("No snapshot_id returned from BrightData trigger response:", trigger_payload)
        return None

    print("Extracting data from LinkedIn URL:", linkedin_url)
    polls = 0
    while polls < _MAX_PROGRESS_POLLS:
        progress_url = f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}"
        try:
            progress_response = _request_with_retries(session, "GET", progress_url, headers=headers)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            print("BrightData progress polling failed after retries:", e)
            return None

        if not progress_response.ok:
            print(
                "BrightData progress request failed.",
                "Status:",
                progress_response.status_code,
                "Body:",
                progress_response.text[:500],
            )
            return None

        try:
            progress_data = progress_response.json()
        except JSONDecodeError as e:
            print("Failed to parse BrightData progress response:", e)
            print("Raw body:", progress_response.text[:500])
            return None

        if progress_data.get("status") == "ready":
            break
        if progress_data.get("status") == "failed":
            print("Data extraction failed.")
            return None
        print(f"Progressing...[{snapshot_id}] >> Status: {progress_data.get('status')}")
        time.sleep(3)
        polls += 1
    else:
        print("BrightData progress polling exceeded max wait; giving up.")
        return None

    time.sleep(3)

    url = f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    params = {"format": "json"}

    try:
        response = _request_with_retries(session, "GET", url, headers=headers, params=params)
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
        print("BrightData snapshot fetch failed after retries:", e)
        return None

    if not response.ok:
        print(
            "BrightData snapshot request failed.",
            "Status:",
            response.status_code,
            "Body:",
            response.text[:500],
        )
        return None

    try:
        data = response.json()
    except JSONDecodeError as e:
        print("Failed to parse BrightData snapshot response:", e)
        print("Raw body:", response.text[:500])
        return None

    print("[+] LinkedIn data extracted successfully.")
    return data
