import os
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import tools_condition
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

from src.config.configer import Configer

from src.ai.state.states import EmailState
from src.ai.nodes.route_nodes import find_conversation_intent, schedule_route_identifier
from src.ai.nodes.response_nodes import (
    estimate_human_time_llm,
    conversational_llm,
    manual_schedule_confirmer,
    automatic_scheduler_agent,
    final_mail_writer
)
from src.ai.edges.edges import route_conversation_intent, route_meeting_schedule_action, check_tools_condition
from src.ai.tools.vector_retrievers import company_data_retriever_tool
from src.ai.tools.calendly_tools import check_calendly_event_tool, available_meeting_dt_checker_tool, booking_schedule_tool

configer = Configer()

os.environ["USER_AGENT"] = "my-langchain-agent/1.0"
_langsmith = configer.get_langchain_api_key()
if _langsmith:
    os.environ["LANGSMITH_API_KEY"] = _langsmith
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "email-automation-ai"


def get_reply_agent_graph():
    data_retriever_tools = [company_data_retriever_tool()]
    meeting_scheduler_tools = [
        check_calendly_event_tool,
        available_meeting_dt_checker_tool,
        booking_schedule_tool,
        company_data_retriever_tool(),
    ]

    conn = sqlite3.connect("src/database/email_agent_memory.db", check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    graph = StateGraph(EmailState)
    graph.add_node("conversational_llm", conversational_llm)
    graph.add_node("data_retriever_tools", ToolNode(tools=data_retriever_tools))
    # graph.add_node("calendly_checker_tools", ToolNode(tools=calendly_checker_tools))
    graph.add_node("meeting_scheduler_tools", ToolNode(tools=meeting_scheduler_tools))
    graph.add_node("estimate_human_time_llm", estimate_human_time_llm)
    graph.add_node("find_conversation_intent", find_conversation_intent)
    # graph.add_node("schedule_route_identifier", schedule_route_identifier)
    # graph.add_node("manual_schedule_confirmer", manual_schedule_confirmer)
    graph.add_node("automatic_scheduler_agent", automatic_scheduler_agent)
    graph.add_node("final_mail_writer", final_mail_writer)

    graph.add_edge(START, "find_conversation_intent")
    graph.add_conditional_edges(
        "find_conversation_intent",
        route_conversation_intent,
        {"Client Interested": "automatic_scheduler_agent", "Client NOT Interested": "conversational_llm"},
    )
    # graph.add_conditional_edges(
    #     "schedule_route_identifier",
    #     route_meeting_schedule_action,
    #     {
    #         "Manual Scheduling": "manual_schedule_confirmer",  # Check client successfully create the meeting or not,
    #         "API-Based Scheduling": "automatic_scheduler_agent",  # Sechule the meeting useing API. Take infor.
    #     },
    # )

    # Conversation LLM tool conditions
    graph.add_conditional_edges(
        "conversational_llm",
        check_tools_condition,
        {"use_tools": "data_retriever_tools", "final_mail_writer": "final_mail_writer"},
    )
    graph.add_edge("data_retriever_tools", "conversational_llm")

    # # Manual Schedule Confirmer tool conditions
    # graph.add_conditional_edges(
    #     "manual_schedule_confirmer",
    #     check_tools_condition,
    #     {"use_tools": "calendly_checker_tools", "final_mail_writer": "final_mail_writer"},
    # )
    # graph.add_edge("calendly_checker_tools", "manual_schedule_confirmer")

    # Automatic Scheduler tool conditions
    graph.add_conditional_edges(
        "automatic_scheduler_agent",
        check_tools_condition,
        {"use_tools": "meeting_scheduler_tools", "final_mail_writer": "final_mail_writer"},
    )
    graph.add_edge("meeting_scheduler_tools", "automatic_scheduler_agent")
    
    graph.add_edge("final_mail_writer", "estimate_human_time_llm")
    # End
    graph.add_edge("estimate_human_time_llm", END)
    graph_builder = graph.compile(checkpointer=checkpointer)
    return graph_builder
