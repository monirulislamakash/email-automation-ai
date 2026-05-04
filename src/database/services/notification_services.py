from src.database.session import get_session
from src.database.models.notificatoins import Notifications
from sqlalchemy.exc import IntegrityError


def add_notification(notification: dict):
    """
    Args:
        prompt_name (str): ex. useful links extractor prompt
        value (str):
    """
    with get_session() as session:
        new_prompt = Notifications(notification=notification)
        try:
            session.add(new_prompt)
            session.commit()
            print("New notification added successfully.")
            return new_prompt
        except IntegrityError as e:
            session.rollback()
            print("An error occurred:", e)
            return False


def get_all_notifications():
    """
    Retrieve all notifications ordered by date in descending order (newest first).

    Returns:
        list: List of Notifications objects ordered by date (newest first)
    """
    with get_session() as session:
        notifications = session.query(Notifications).order_by(Notifications.date.desc()).all()
        return notifications
