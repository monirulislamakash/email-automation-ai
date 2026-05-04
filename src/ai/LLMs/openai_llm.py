from langchain_openai import ChatOpenAI
from src.config.configer import Configer

configer = Configer()


def _openai_api_key():
    key = configer.get_openai_api_key()
    if not key:
        raise RuntimeError(
            "OpenAI API key is missing. Set OPENAI_API_KEY in `.env` / the environment, "
            "or add a `OPENAI_API_KEY` row in the app credentials table."
        )
    return key


def get_llm():
    return ChatOpenAI(model="gpt-5.1", temperature=0.2, openai_api_key=_openai_api_key(), timeout=300)


def get_decision_llm():
    return ChatOpenAI(model="gpt-4o", temperature=0, openai_api_key=_openai_api_key(), timeout=60)
