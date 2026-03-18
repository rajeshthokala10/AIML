"""
05. Advanced Features - Practice Code
Covers: Streaming, subgraphs, error handling with fallback.

Run: python practice.py
"""

from typing import TypedDict, Literal

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, MessagesState, START, END


# --- Subgraph state ---
class SubState(TypedDict):
    messages: list
    step: str


# --- Main graph state ---
class MainState(TypedDict):
    messages: list
    step: str


# --- Subgraph nodes ---
def sub_node_a(state: SubState) -> dict:
    return {"messages": [AIMessage(content="[Sub A]")], "step": "a"}


def sub_node_b(state: SubState) -> dict:
    return {"messages": [AIMessage(content="[Sub B]")], "step": "b"}


# --- Main graph nodes ---
def main_node(state: MainState) -> dict:
    return {"messages": [AIMessage(content="[Main]")], "step": "main"}


def subgraph_node(state: MainState) -> dict:
    """Invoke subgraph as a node."""
    subgraph = StateGraph(SubState)
    subgraph.add_node("a", sub_node_a)
    subgraph.add_node("b", sub_node_b)
    subgraph.add_edge(START, "a")
    subgraph.add_edge("a", "b")
    subgraph.add_edge("b", END)
    sub_app = subgraph.compile()

    sub_input = {"messages": state["messages"], "step": ""}
    result = sub_app.invoke(sub_input)
    return {"messages": result["messages"], "step": "subgraph"}


def fallback_node(state: MainState) -> dict:
    """Fallback when primary fails."""
    return {"messages": [AIMessage(content="[Fallback] Something went wrong, using fallback.")]}


def maybe_fail_node(state: MainState) -> dict:
    """Simulates failure for demo."""
    last = state["messages"][-1]
    content = getattr(last, "content", "") or ""
    if "fail" in content.lower():
        raise ValueError("Simulated failure")
    return {"messages": [AIMessage(content="[OK] Primary path succeeded.")]}


def route_after_main(state: MainState) -> Literal["subgraph", "end"]:
    return "subgraph" if state.get("step") == "main" else "end"


# --- Build graph with subgraph and error handling ---
def build_graph():
    graph = StateGraph(MainState)
    graph.add_node("main", main_node)
    graph.add_node("subgraph", subgraph_node)
    graph.add_node("fallback", fallback_node)
    graph.add_edge(START, "main")
    graph.add_edge("main", "subgraph")
    graph.add_edge("subgraph", END)
    return graph.compile()


def route_to_primary_or_fallback(state: MainState) -> Literal["primary", "fallback"]:
    """Route to fallback when user says 'fail' (avoids exception in primary)."""
    msgs = state.get("messages", [])
    last = msgs[-1] if msgs else None
    content = getattr(last, "content", str(last) or "") or ""
    return "fallback" if "fail" in content.lower() else "primary"


def demo_streaming():
    """Stream state updates."""
    print("=== Streaming (stream_mode='values') ===\n")
    graph = StateGraph(MainState)
    graph.add_node("main", main_node)
    graph.add_edge(START, "main")
    graph.add_edge("main", END)
    app = graph.compile()

    for i, chunk in enumerate(app.stream({"messages": [HumanMessage(content="Hi")], "step": ""}, stream_mode="values")):
        print(f"Chunk {i+1}: step={chunk.get('step')}, messages={len(chunk.get('messages', []))}")


def demo_subgraph():
    """Run graph with subgraph."""
    print("\n=== Subgraph ===\n")
    app = build_graph()
    result = app.invoke({"messages": [HumanMessage(content="Go")], "step": ""})
    print("Messages:", [m.content for m in result["messages"]])


def demo_fallback():
    """Run with conditional fallback (route to fallback when user says 'fail')."""
    print("\n=== Error handling (fallback path) ===\n")
    graph = StateGraph(MainState)
    graph.add_node("primary", maybe_fail_node)
    graph.add_node("fallback", fallback_node)
    graph.add_conditional_edges(START, route_to_primary_or_fallback, {"primary": "primary", "fallback": "fallback"})
    graph.add_edge("primary", END)
    graph.add_edge("fallback", END)
    app = graph.compile()

    r1 = app.invoke({"messages": [HumanMessage(content="ok")], "step": ""})
    print("Normal:", r1["messages"][-1].content)

    r2 = app.invoke({"messages": [HumanMessage(content="please fail")], "step": ""})
    print("With fail:", r2["messages"][-1].content)


if __name__ == "__main__":
    demo_streaming()
    demo_subgraph()
    demo_fallback()
