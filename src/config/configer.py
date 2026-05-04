import os

from src.database.services.credential_services import get_cred_by_name


class Configer:
    def __init__(self):
        pass

    def get_openai_api_key(self):
        stored = get_cred_by_name("OPENAI_API_KEY")
        if stored:
            return stored
        return os.getenv("OPENAI_API_KEY")

    def get_instantly_api_key(self):
        return get_cred_by_name("INSTANTLY_AI_API_KEY")

    def get_brightdata_api_key(self):
        stored = get_cred_by_name("BRIGHTDATA_API_KEY")
        if stored:
            return stored
        return os.getenv("BRIGHTDATA_API_KEY")
    
    def get_pinecone_api_key(self):
        return get_cred_by_name("PINECONE_API_KEY")

    def get_calendly_api_key(self):
        return get_cred_by_name("CALENDLY_API_KEY")

    def get_langchain_api_key(self):
        return get_cred_by_name("LANGCHAIN_API_KEY")
