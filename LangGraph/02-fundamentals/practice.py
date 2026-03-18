"""
02. LangGraph Fundamentals - Practice Code
Covers: StateGraph, nodes, edges (unconditional + conditional), custom state.
Run: python practice.py
"""

from typing import TypedDict, Annotated, Literal

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages


# --- Custom state with reducer ---
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    count: int


# --- Nodes ---
def node_a(state: AgentState) -> dict:
    """First node: echoes and increments counter."""
    return {
        "messages": [AIMessage(content=f"[Node A] Received {len(state['messages'])} messages. Count={state.get('count', 0)}")],
        "count": state.get("count", 0) + 1,
    }


def node_b(state: AgentState) -> dict:
    """Second node: adds final response."""
    return {
        "messages": [AIMessage(content=f"[Node B] Count is now {state.get('count', 0)}. Done!")],
        "count": state.get("count", 0) + 1,
    }


def short_response_node(state: AgentState) -> dict:
    """Used when message is short (< 20 chars)."""
    last = state["messages"][-1]
    text = getattr(last, "content", str(last)) or ""
    return {"messages": [AIMessage(content=f"Short query: '{text[:20]}'")]}


def long_response_node(state: AgentState) -> dict:
    """Used when message is long (>= 20 chars)."""
    last = state["messages"][-1]
    text = getattr(last, "content", str(last)) or ""
    return {"messages": [AIMessage(content=f"Long query ({len(text)} chars), processing...")]}


def route_by_length(state: AgentState) -> Literal["short", "long"]:
    """Conditional routing: branch based on last message length."""
    last = state["messages"][-1]
    text = getattr(last, "content", str(last)) or ""
    return "short" if len(text) < 20 else "long"


# --- Build graphs ---
def build_linear_graph():
    """Linear: START → node_a → node_b → END"""
    graph = StateGraph(AgentState)
    graph.add_node("node_a", node_a)
    graph.add_node("node_b", node_b)
    graph.add_edge(START, "node_a")
    graph.add_edge("node_a", "node_b")
    graph.add_edge("node_b", END)
    return graph.compile()


def build_conditional_graph():
    """Conditional: START → route by length → short/long → END"""
    graph = StateGraph(AgentState)
    graph.add_node("short", short_response_node)
    graph.add_node("long", long_response_node)
    graph.add_conditional_edges(START, route_by_length, {"short": "short", "long": "long"})
    graph.add_edge("short", END)
    graph.add_edge("long", END)
    return graph.compile()


if __name__ == "__main__":
    print("=== Linear Graph (START → A → B → END) ===\n")
    app_linear = build_linear_graph()
    result = app_linear.invoke({
        "messages": [HumanMessage(content="Hello")],
        "count": 0,
    })
    print("Messages:", [m.content for m in result["messages"]])
    print("Final count:", result["count"])

    print("\n=== Conditional Graph (route by message length) ===\n")
    app_cond = build_conditional_graph()

    r1 = app_cond.invoke({"messages": [HumanMessage(content="Hi")], "count": 0})
    print("Short input 'Hi':", r1["messages"][-1].content)

    r2 = app_cond.invoke({"messages": [HumanMessage(content="This is a much longer message for testing")], "count": 0})
    print("Long input:", r2["messages"][-1].content)
