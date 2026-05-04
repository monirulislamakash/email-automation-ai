from pydantic import BaseModel, Field
from langgraph.graph.message import Annotated, add_messages
from langchain_core.messages import HumanMessage, AIMessage, AnyMessage, SystemMessage, ToolMessage
from typing import Optional, Literal, List


class ScraperState(BaseModel):
    links: List[str] = Field(description="List of useful URLs extracted from the page (max 6).")


class EmailState(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages]
    draft_mail: Optional[str] = None  # Draft reply email
    reply_mail: Optional[str] = None  # Reply Mail Content
    estimated_human_time: Optional[float] = None  # Estimated human mail writing time

    conversation_intent: Optional[str] = None  # Interested, NOT Interested
    schedule_method: Optional[str] = None  # Manual (via client), Automatic (API)

    tool_executed: bool = False


class IntentResponse(BaseModel):
    intent: Literal["interested", "not interested"] = Field(description="Decide client interest to set a meeting or not")


class ScheduleActionResponse(BaseModel):
    schedule_intent: Literal["manual", "automatic"] = Field(
        description="Whether meeting was manually scheduled by client or needs automatic scheduling"
    )


class TimeEstimate(BaseModel):
    total_minutes: float = Field(description="Total estimated time in minutes", gt=0, le=120)  # Greater than 0 validation
