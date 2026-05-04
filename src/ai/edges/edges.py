from src.ai.state.states import EmailState


def route_conversation_intent(state: EmailState):
    if state.conversation_intent == "interested":
        return "Client Interested"
    else:
        return "Client NOT Interested"


def route_meeting_schedule_action(state: EmailState):
    if state.schedule_method == "manual":
        return "Manual Scheduling"
    else:
        return "API-Based Scheduling"


def check_tools_condition(state: EmailState):
    last_message = state.messages[-1]
    # If tool already used before → skip tool call
    if state.tool_executed is True:
        state.tool_executed = False
        return "final_mail_writer"

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        # Mark tool as used
        state.tool_executed = True
        return "use_tools"

    return "final_mail_writer"
