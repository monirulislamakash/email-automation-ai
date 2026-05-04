from src.ai.graph.reply_agent_graph import get_reply_agent_graph


def call_reply_agent(client_reply: str, thread_id: str):
    print("============Reply Agent Called============")
    config = {"configurable": {"thread_id": thread_id}}
    graph_builder = get_reply_agent_graph()

    results = graph_builder.invoke({"messages": client_reply}, config=config)
    reply_mail = results["reply_mail"]  # .replace("\n", "<br>")
    estimated_human_time = results["estimated_human_time"]
    return estimated_human_time, reply_mail
