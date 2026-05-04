import asyncio
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from flask import json
from src.ai.content_generator_agent import generate_content
from src.ai.content_generator_agent import link_extractor_agent
from src.ai.prompts.user_prompts import useful_links_extractor_prompt
from src.ai.prompts.user_prompts import each_page_data_extractor_prompt
from src.ai.prompts.user_prompts import all_page_summarizer_prompt


async def get_text_data(url):
    async with AsyncWebCrawler(verbose=True) as crawler:
        if url.startswith("http://"):
            url = url.replace("http://", "https://")
        elif "https://" not in url:
            url = "https://" + url
        print("scraping url", url)
        result = await crawler.arun(url)
        return result.markdown


async def get_html_data(url):
    async with AsyncWebCrawler() as crawler:
        if url.startswith("http://"):
            url = url.replace("http://", "https://")
        elif "https://" not in url:
            url = "https://" + url
        print("scraping url", url)
        result = await crawler.arun(
            url=url, config=CrawlerRunConfig(cache_mode="bypass")
        )
        if result.success:
            print("Raw HTML Content:")
            # print(result.html)
            return result.html
        else:
            print(f"Failed to crawl: {result.error_message}")


def get_output(url: str) -> str:
    """this function fetch raw text data from url. then analyze with AI to extract useful information."""

    results = asyncio.run(get_text_data(url))
    prompt = each_page_data_extractor_prompt(results)
    content = generate_content(prompt)
    print("-----------------------------------------")
    print(content)
    print("-----------------------------------------")
    return content


def scrape_website_data(url: str) -> str:
    data = ""
    urls = [url]
    results = asyncio.run(get_html_data(url))
    if results:
        soup = BeautifulSoup(results, "html.parser")
        links = []

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            full_url = urljoin(url, href)
            links.append(full_url)

        links = list(set(links))
        prompt = useful_links_extractor_prompt(links)
        useful_links = link_extractor_agent(prompt)
        print("Useful Links: ", useful_links)
        try:
            urls = urls + useful_links
        except Exception:
            print("Error decoding JSON from useful links response.")

    for i, url in enumerate(urls):
        print(f"[{i + 1}] Processing URL:", url)
        output_results = get_output(url)
        if output_results:
            # print("Output Results:", output_results)
            data += f"page url: {url} \nData: {output_results}\n\n"

        # print("=========================================")

    summarizer_prompt = all_page_summarizer_prompt(data)
    final_data = generate_content(prompt=summarizer_prompt)
    print("Final Results: \n\n", final_data)
    print("==" * 50)
    return final_data
