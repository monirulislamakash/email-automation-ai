from langchain_core.messages import SystemMessage, ToolMessage, AIMessage, HumanMessage

from src.ai.LLMs.openai_llm import get_llm, get_decision_llm
from src.ai.state.states import EmailState, TimeEstimate
from src.ai.prompts.agent_prompts import estimate_human_time_prompt, schedule_confirmer_prompt, scheduler_booking_agent_prompt
from src.ai.prompts.user_prompts import conversational_llm_system_prompt, final_reply_agent_system_prompt
from src.ai.tools.vector_retrievers import company_data_retriever_tool
from src.ai.tools.calendly_tools import check_calendly_event_tool, available_meeting_dt_checker_tool, booking_schedule_tool

calendly_checker_tools = [check_calendly_event_tool]
meeting_scheduler_tools = [
    available_meeting_dt_checker_tool,
    booking_schedule_tool,
]


def estimate_human_time_llm(state: EmailState) -> dict:
    print("-------Estimated Human Time Calculator Called-------")
    # time_llm = llm.with_structured_output(TimeEstimate)
    # prompt = estimate_human_time_prompt(state)
    # response = time_llm.invoke(prompt)
    # print(f"-------Estimated Human Time: {response.total_minutes}")
    # return {"estimated_human_time": response.total_minutes}
    import random

    return {"estimated_human_time": float(random.randint(16, 25))}


def conversational_llm(state: EmailState) -> dict:
    print("-------Conversational LLM Agent Called-------")
    llm = get_llm()
    data_retriever_tools = [company_data_retriever_tool()]
    all_msgs = state.messages
    human_msgs = [m for m in all_msgs if isinstance(m, HumanMessage)]
    first_human = human_msgs[0] if human_msgs else None

    # Take a small tail of the conversation plus the very first human message
    tail_candidates = all_msgs[-10:] if len(all_msgs) > 10 else all_msgs
    ordered_msgs = []
    if first_human and first_human in all_msgs:
        ordered_msgs.append(first_human)
    for m in tail_candidates:
        if m is not first_human:
            ordered_msgs.append(m)

    conversation_history = "\n".join(
        f"[{'CLIENT' if isinstance(m, HumanMessage) else 'AGENT' if isinstance(m, AIMessage) else 'TOOL'}] {m.content}"
        for m in ordered_msgs
    )

    # Check if the last AI message already issued a company_data_vectordb tool call
    last_msg = all_msgs[-1] if all_msgs else None
    has_company_data_tool_result = False
    if isinstance(last_msg, ToolMessage):
        print("-----------Vector DB tool was called-----------")
        has_company_data_tool_result = True

    system_prompt = conversational_llm_system_prompt()
    human_content = f"Here is the recent conversation (most recent messages last):\n{conversation_history}"

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_content),
    ]

    # If we already have a tool result, don't bind tools again – just use the data
    if has_company_data_tool_result:
        response = llm.invoke(messages)
    else:
        llm_with_data_retriever_tools = llm.bind_tools(data_retriever_tools)
        response = llm_with_data_retriever_tools.invoke(messages)

    return {"messages": [response], "draft_mail": response.content}


# Node: Check client successfully create the meeting or not and send reply based on it
def manual_schedule_confirmer(state: EmailState):
    print("-------Manual Schedule Confirmer Called-------")
    llm = get_llm()
    all_msgs = state.messages
    human_msgs = [m for m in all_msgs if isinstance(m, HumanMessage)]
    first_human = human_msgs[0] if human_msgs else None

    tail_candidates = all_msgs[-5:] if len(all_msgs) > 5 else all_msgs
    ordered_msgs = []
    if first_human and first_human in all_msgs:
        ordered_msgs.append(first_human)
    for m in tail_candidates:
        if m is not first_human:
            ordered_msgs.append(m)

    conversation_history = "\n".join(
        f"[{'CLIENT' if isinstance(m, HumanMessage) else 'AGENT' if isinstance(m, AIMessage) else 'TOOL'}] {m.content}"
        for m in ordered_msgs
    )

    instructions = schedule_confirmer_prompt()

    # If Calendly tool was already called, compose a final reply without calling tools again
    try:
        tool_result_text = None
        last_msg = state.messages[-1] if state.messages else None
        if isinstance(last_msg, ToolMessage) and getattr(last_msg, "name", None) == "check_calendly_event_tool":
            tool_result_text = str(last_msg.content)
        if tool_result_text:
            human_content = f"""
Here is the relevant conversation snippet (most recent messages last):
{conversation_history}

Here is the result from the Calendly event check tool:
{tool_result_text}

TASK:
- Do NOT call any tools again.
- Based on the tool result and the client's latest message, write a short, friendly reply.
- Clearly confirm whether the meeting is booked or not, and tell the client the next simple step if needed.
- Keep it concise, professional, and aligned with Ray Advertising's tone.
"""
            messages = [
                SystemMessage(content=instructions),
                HumanMessage(content=human_content),
            ]
            response = llm.invoke(messages)
            return {"messages": [response], "draft_mail": response.content}
    except Exception as _e:
        print(_e)

    llm_with_calendly_checker_tool = llm.bind_tools(calendly_checker_tools)
    messages = [
        SystemMessage(content=instructions),
        HumanMessage(content=conversation_history),
    ]
    response = llm_with_calendly_checker_tool.invoke(messages)
    return {"messages": [response], "draft_mail": response.content}


# Node: Schedule the meeting using API. Find necessary info. Ask if not have all kind of info. Reply mail
def automatic_scheduler_agent(state: EmailState):
    print("-------Automatic Schedule Agent Called-------")
    llm = get_llm()
    all_msgs = state.messages
    human_msgs = [m for m in all_msgs if isinstance(m, HumanMessage)]
    first_human = human_msgs[0] if human_msgs else None

    # Take a small tail of the conversation plus the very first human message
    tail_candidates = all_msgs[-15:] if len(all_msgs) > 15 else all_msgs
    ordered_msgs = []
    if first_human and first_human in all_msgs:
        ordered_msgs.append(first_human)
    for m in tail_candidates:
        if m is not first_human:
            ordered_msgs.append(m)

    conversation_history = "\n".join(
        f"[{'CLIENT' if isinstance(m, HumanMessage) else 'AGENT' if isinstance(m, AIMessage) else 'TOOL'}] {m.content}"
        for m in ordered_msgs
    )
    system_prompt = scheduler_booking_agent_prompt()
    try:
        tool_result_text = None
        last_msg = state.messages[-1] if state.messages else None
        if isinstance(last_msg, ToolMessage):
            tool_result_text = str(last_msg.content)
        if tool_result_text:
            human_content = f"""
Here is the relevant conversation snippet (most recent messages last):
{conversation_history}

Here is the result from the Calendly tool:
{tool_result_text}

TASK:
- Do NOT call any tools again.
- Based on the tool result and the client's latest message, write a short, friendly reply.
- Clearly confirm what the current booking status is and, if needed, suggest the next simple step.
- Keep it concise, professional, and aligned with Ray Advertising's tone.
"""
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_content),
            ]
            response = llm.invoke(messages)
            return {"messages": [response], "draft_mail": response.content}
    except Exception as _e:
        print(_e)
    llm_with_calendly_booking_tool = llm.bind_tools(meeting_scheduler_tools)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=conversation_history),
    ]
    response = llm_with_calendly_booking_tool.invoke(messages)
    return {"messages": [response], "draft_mail": response.content}


def final_mail_writer(state: EmailState) -> dict:
    print("-------Final Mail Writer Agent Called-------")
    llm2 = get_decision_llm()
    system_prompt = final_reply_agent_system_prompt()

    # Recent conversation (focus on last few messages)
    relevant = [m for m in state.messages if isinstance(m, (HumanMessage, AIMessage))]
    recent = relevant[-6:] if len(relevant) > 6 else relevant
    conversation_history = "\n".join(f"[{'CLIENT' if isinstance(m, HumanMessage) else 'AGENT'}] {m.content}" for m in recent)

    # Explicit focus on last client + last agent message
    last_client = next((m for m in reversed(relevant) if isinstance(m, HumanMessage)), None)
    last_agent = next((m for m in reversed(relevant) if isinstance(m, AIMessage)), None)

    focused_view_parts = []
    if last_client:
        focused_view_parts.append(f"[LAST CLIENT MESSAGE]\n{last_client.content}")
    if last_agent:
        focused_view_parts.append(f"[LAST AGENT REPLY]\n{last_agent.content}")
    focused_view = "\n\n".join(focused_view_parts) if focused_view_parts else ""

    human_instruction = f"""
Here is the current draft reply email that has already been generated:
{state.draft_mail}

Previous conversation history: {conversation_history}
- Do not use <p> tags;
- Don't use so much <br> tag. Make it like it was write by human.
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_instruction),
    ]
    response = llm2.invoke(messages)
    return {"messages": [response], "reply_mail": response.content}
