from langchain_openai import OpenAIEmbeddings
from src.config.configer import Configer


configer = Configer()


def get_openai_embeddings():
    api_key = configer.get_openai_api_key()
    if not api_key:
        raise RuntimeError(
            "OpenAI API key is missing (needed for embeddings). Set OPENAI_API_KEY in `.env` "
            "or in the app credentials table."
        )
    return OpenAIEmbeddings(openai_api_key=api_key, model="text-embedding-3-large")
