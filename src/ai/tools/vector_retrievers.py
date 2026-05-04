import os
from langchain.tools.retriever import create_retriever_tool
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
from src.config.configer import Configer
from src.ai.embeddings.embeddings import get_openai_embeddings

configer = Configer()

PINECONE_API_KEY = configer.get_pinecone_api_key()
if PINECONE_API_KEY:
    os.environ.setdefault("PINECONE_API_KEY", PINECONE_API_KEY)
    pc = Pinecone(api_key=PINECONE_API_KEY)
else:
    pc = None


def company_data_retriever_tool():
    """Get Information about ray adverting company full data. Everything included here."""
    embeddings = get_openai_embeddings()
    company_data_index_name = "company-data-index"
    company_db = PineconeVectorStore.from_existing_index(index_name=company_data_index_name, embedding=embeddings)
    company_data_retriever = company_db.as_retriever(
        search_type="similarity_score_threshold", search_kwargs={"k": 1, "score_threshold": 0.7}
    )
    company_data_retriever_tool = create_retriever_tool(
        retriever=company_data_retriever,
        name="company_data_vectordb",
        description="Get Information about ray adverting company. FAQ data. Everything included here.",
    )
    return company_data_retriever_tool


def get_company_vector_data(query):
    results_doc = company_data_retriever_tool().invoke(query)
    return results_doc.strip()
