from src.ai.LLMs.openai_llm import get_llm
from src.ai.state.states import ScraperState


def generate_content(prompt: str) -> str:
    print("Generating content...")
    llm = get_llm()
    response = llm.invoke(prompt)
    return response.content


def link_extractor_agent(prompt: str) -> list:
    llm = get_llm()
    llm_scraper_state = llm.with_structured_output(ScraperState)
    response = llm_scraper_state.invoke(prompt)
    return response.links
