from src.database.session import get_session
from src.database.models.prompts import GlobalPrompts, CustomPrompts
from sqlalchemy.exc import IntegrityError


# Global prompt
def add_global_prompt(prompt_name: str, prompt_value: str):
    """
    Args:
        prompt_name (str): ex. useful links extractor prompt
        value (str):
    """
    with get_session() as session:
        new_prompt = GlobalPrompts(prompt_name=prompt_name, prompt_value=prompt_value)
        try:
            session.add(new_prompt)
            session.commit()
            print(f"New prompt {prompt_name} added successfully.")
            return new_prompt
        except IntegrityError as e:
            session.rollback()
            print("An error occurred:", e)
            return False


def get_global_prompt(prompt_name: str):
    """
    Args:
        prompt_name (str): ex. useful links extractor prompt
    """
    with get_session() as session:
        prompt = session.query(GlobalPrompts).filter_by(prompt_name=prompt_name).first()
        if prompt:
            return prompt.prompt_value
        else:
            return None


def get_all_global_prompts():
    with get_session() as session:
        prompts = session.query(GlobalPrompts).all()
        return prompts


def update_global_prompt(prompt_name: str, prompt_value: str):
    """
    Args:
        prompt_name (str): ex. useful links extractor prompt
    """
    with get_session() as session:
        prompt = session.query(GlobalPrompts).filter_by(prompt_name=prompt_name).first()
        if prompt:
            prompt.prompt_value = prompt_value
            session.commit()
            print(f"prompt {prompt_name} value updated")
            return prompt
        else:
            print(f"No prompt found with name {prompt_name}.")
            return False


def update_global_prompt_status(prompt_name: str, status: str):
    with get_session() as session:
        prompt = session.query(GlobalPrompts).filter_by(prompt_name=prompt_name).first()
        if prompt:
            prompt.status = status
            session.commit()
            print(f"prompt {prompt_name} status updated")
            return prompt
        else:
            print(f"No prompt found with name {prompt_name}.")
            return False


def delete_global_prompt(prompt_name: str):
    with get_session() as session:
        prompt = session.query(GlobalPrompts).filter_by(prompt_name=prompt_name).first()
        if prompt:
            session.delete(prompt)
            session.commit()
            print(f"prompt {prompt_name} deleted")
            return True
        else:
            return False


# Custom prompt
def add_custom_prompt(campaign_pk: int, campaign_id: str, prompt_name: str, prompt_value: str):
    """
    Args:
        prompt_name (str): ex. useful links extractor prompt
        value (str):
    """
    with get_session() as session:
        existing_prompt = session.query(CustomPrompts).filter_by(prompt_name=prompt_name, campaign_id=campaign_id).first()
        if existing_prompt:
            print("Error: A prompt with this name and campaign id already exists.")
            return None
        new_prompt = CustomPrompts(campaign_pk=campaign_pk, campaign_id=campaign_id, prompt_name=prompt_name, prompt_value=prompt_value)
        try:
            session.add(new_prompt)
            session.commit()
            print(f"New custom prompt {prompt_name} added successfully.")
            return new_prompt
        except IntegrityError as e:
            session.rollback()
            print("An error occurred:", e)
            return False


def get_custom_prompt(id: int, prompt_name: str):
    """
    Args:
        prompt_name (str): ex. useful links extractor prompt
    """
    with get_session() as session:
        prompt = session.query(CustomPrompts).filter_by(prompt_name=prompt_name, campaign_pk=id).first()
        if prompt:
            return prompt
        else:
            return None


def get_all_custom_prompts():
    with get_session() as session:
        prompts = session.query(CustomPrompts).all()
        return prompts


def update_custom_prompt(campaign_id: str, prompt_name: str, prompt_value: str):
    """
    Args:
        prompt_name (str): ex. useful links extractor prompt
    """
    with get_session() as session:
        prompt = session.query(CustomPrompts).filter_by(prompt_name=prompt_name, campaign_id=campaign_id).first()
        if prompt:
            prompt.prompt_value = prompt_value
            session.commit()
            print(f"prompt {prompt_name} value updated")
            return prompt
        else:
            print(f"No prompt found with name {prompt_name}.")
            return False


def change_custom_prompt_status(campaign_id: str, prompt_name: str, status: str):
    """
    Args:
        prompt_name (str): ex. useful links extractor prompt
    """
    with get_session() as session:
        prompt = session.query(CustomPrompts).filter_by(prompt_name=prompt_name, campaign_id=campaign_id).first()
        if prompt:
            prompt.status = status
            session.commit()
            print(f"prompt {prompt_name} value updated")
            return prompt
        else:
            print(f"No prompt found with name {prompt_name}.")
            return False


def delete_custom_prompt(campaign_id: str, prompt_name: str):
    with get_session() as session:
        prompt = session.query(CustomPrompts).filter_by(prompt_name=prompt_name, campaign_id=campaign_id).first()
        if prompt:
            session.delete(prompt)
            session.commit()
            return True
        else:
            return False
