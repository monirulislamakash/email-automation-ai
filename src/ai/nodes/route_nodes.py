from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.ai.LLMs.openai_llm import get_decision_llm
from src.ai.state.states import EmailState, IntentResponse, ScheduleActionResponse
from src.ai.prompts.agent_prompts import conversation_intent_prompt, schedule_route_identifier_prompt


def find_conversation_intent(state: EmailState) -> dict:
    print("-------Conversation Intent Finder Called-------")
    llm = get_decision_llm()
    intent_llm = llm.with_structured_output(IntentResponse)
    relevant = [m for m in state.messages if isinstance(m, (HumanMessage, AIMessage))]
    relevant = relevant[-10:]

    conversation_history = "\n".join(f"[{'CLIENT' if isinstance(m, HumanMessage) else 'AGENT'}] {m.content}" for m in relevant)
    instructions = conversation_intent_prompt()
    messages = [
        SystemMessage(content=instructions),
        HumanMessage(content=f"Here is full CONVERSATION HISTORY: {conversation_history}"),
    ]
    response = intent_llm.invoke(messages)
    print(f"-------Conversation Intent: {response.intent}")
    return {"conversation_intent": response.intent}


def schedule_route_identifier(state: EmailState) -> dict:
    print("-------Schedule Route Identifier Called-------")
    llm = get_decision_llm()
    schedule_intent_llm = llm.with_structured_output(ScheduleActionResponse)
    relevant = [m for m in state.messages if isinstance(m, (HumanMessage, AIMessage))]
    relevant = relevant[-10:]

    conversation_history = "\n".join(f"[{'CLIENT' if isinstance(m, HumanMessage) else 'AGENT'}] {m.content}" for m in relevant)
    instructions = schedule_route_identifier_prompt()
    messages = [
        SystemMessage(content=instructions),
        HumanMessage(content=f"Here is full CONVERSATION HISTORY: {conversation_history}"),
    ]
    response = schedule_intent_llm.invoke(messages)
    print(f"-------Identifier Route Schedule: {response.schedule_intent}")
    return {"schedule_method": response.schedule_intent}
