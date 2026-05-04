import os
from datetime import datetime


def write_campaign_log(campaign_id: str, message: str) -> None:
    """Write Log

    Args:
        message (str): Log Message
    """
    log_dir = os.path.join("logs", "campaigns")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    datestamp = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"{campaign_id}.log")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} | {message}\n"

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line)
    print(line, end="")


def write_agent_log(message: str) -> None:
    """Write Log

    Args:
        message (str): Log Message
    """
    log_dir = os.path.join("logs", "agents")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    datestamp = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"{datestamp}.log")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} | {message}\n"

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line)
    print(line, end="")
