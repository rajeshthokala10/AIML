"""
07. Projects - Complete Chatbot Example
A beginner-to-intermediate project: linear graph with memory.

Run: python main.py
"""

from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import MemorySaver

import os


def build_chatbot(use_memory: bool = True):
    """Build chatbot graph. Uses real LLM if OPENAI_API_KEY is set."""
    graph = StateGraph(MessagesState)

    if os.getenv("OPENAI_API_KEY"):
        model = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

        def llm_node(state):
            response = model.invoke(state["messages"])
            return {"messages": [response]}

        graph.add_node("llm", llm_node)
    else:
        # Mock fallback
        def mock_node(state):
            last = state["messages"][-1]
            content = getattr(last, "content", "") or ""
            return {"messages": [AIMessage(content=f"Echo: {content}")]}

        graph.add_node("llm", mock_node)

    graph.add_edge(START, "llm")
    graph.add_edge("llm", END)

    checkpointer = MemorySaver() if use_memory else None
    return graph.compile(checkpointer=checkpointer)


def main():
    app = build_chatbot()
    config = {"configurable": {"thread_id": "demo"}}

    print("Chatbot (type 'quit' to exit)\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            break
        if not user_input:
            continue

        result = app.invoke(
            {"messages": [HumanMessage(content=user_input)]},
            config,
        )
        reply = result["messages"][-1].content
        print(f"Bot: {reply}\n")


if __name__ == "__main__":
    main()
