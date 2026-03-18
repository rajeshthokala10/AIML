"""
03. State and Memory - Practice Code
Covers: MemorySaver checkpointer, multi-turn conversation, custom reducer.
Run: python practice.py
"""

from typing import TypedDict, Annotated

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver


# --- State with add_messages reducer ---
class ChatState(TypedDict):
    messages: Annotated[list, add_messages]


# --- Custom reducer: keep only last N messages ---
def keep_last_n(n: int):
    def reducer(left: list, right: list) -> list:
        combined = (left or []) + (right or [])
        return combined[-n:] if len(combined) > n else combined
    return reducer


class TrimmedState(TypedDict):
    messages: Annotated[list, keep_last_n(3)]


# --- Nodes ---
def chatbot_node(state: ChatState) -> dict:
    """Simple echo-style response (replace with real LLM in production)."""
    last = state["messages"][-1]
    content = getattr(last, "content", str(last)) or ""
    reply = f"Echo: You said '{content}'"
    return {"messages": [AIMessage(content=reply)]}


# --- Build graph with checkpointer ---
def build_graph_with_memory():
    graph = StateGraph(ChatState)
    graph.add_node("chatbot", chatbot_node)
    graph.add_edge(START, "chatbot")
    graph.add_edge("chatbot", END)

    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


if __name__ == "__main__":
    print("=== Multi-turn conversation with MemorySaver ===\n")
    app = build_graph_with_memory()
    config = {"configurable": {"thread_id": "user-123"}}

    # Turn 1
    r1 = app.invoke({"messages": [HumanMessage(content="My name is Alice")]}, config)
    print("Turn 1:", r1["messages"][-1].content)

    # Turn 2 - conversation continues (state persisted)
    r2 = app.invoke({"messages": [HumanMessage(content="What's my name?")]}, config)
    print("Turn 2:", r2["messages"][-1].content)

    # All messages in state (history preserved)
    print("\nFull message history:")
    for m in r2["messages"]:
        role = getattr(m, "type", "?")
        content = getattr(m, "content", str(m))
        print(f"  {role}: {content[:50]}...")
