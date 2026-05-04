from src.database.session import get_session
from src.database.models.credentials import Credentials
from sqlalchemy.exc import IntegrityError


def add_credential(name: str, value: str):
    """
    Args:
        name (str): ex. OPENAI_API_KEY
        value (str):
    """
    with get_session() as session:
        new_cred = Credentials(name=name, value=value)
        try:
            session.add(new_cred)
            session.commit()
            print(f"New cred {name} added successfully.")
            return True
        except IntegrityError as e:
            session.rollback()
            print("An error occurred:", e)
            return False


def get_cred_by_name(name: str):
    """
    Args:
        name (str): ex. OPENAI_API_KEY
    """
    with get_session() as session:
        cred = session.query(Credentials).filter_by(name=name).first()
        if cred:
            return cred.value
        else:
            return None


def get_all_cred():
    with get_session() as session:
        creds = session.query(Credentials).all()
        if creds:
            return creds
        else:
            return None


def update_credential(name: str, new_value: str):
    """
    Args:
        name (str): ex. OPENAI_API_KEY
    """
    with get_session() as session:
        cred = session.query(Credentials).filter_by(name=name).first()
        if cred:
            cred.value = new_value
            session.commit()
            print(f"Cred {name} value updated")
            return True
        else:
            print(f"No cred found with name {name}.")
            return False
