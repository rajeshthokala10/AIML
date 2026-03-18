"""
01. Prerequisites - Practice Code
Covers: Python async, TypedDict, LangChain messages/tools, agent loop concept.
Run: python practice.py
"""

import asyncio
from typing import TypedDict, Annotated


# --- 1. TypedDict for state (used in LangGraph) ---
class SimpleState(TypedDict):
    messages: list
    step_count: int


# --- 2. Async basics (LangGraph supports async) ---
async def async_node(state: SimpleState) -> dict:
    """Simulates async processing - LangGraph nodes can be async."""
    await asyncio.sleep(0.1)  # Simulate I/O
    return {"step_count": state.get("step_count", 0) + 1}


async def main_async():
    state: SimpleState = {"messages": [], "step_count": 0}
    for _ in range(3):
        update = await async_node(state)
        state = {**state, **update}
    print(f"Async: Final step_count = {state['step_count']}")


# --- 3. LangChain-style messages (concept) ---
def create_messages_demo():
    """Messages structure used in LangGraph MessagesState."""
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

    messages = [
        SystemMessage(content="You are a helpful assistant."),
        HumanMessage(content="Hello!"),
        AIMessage(content="Hi! How can I help?"),
    ]
    print(f"Messages: {len(messages)} items")
    return messages


# --- 4. Tool definition (LangChain @tool pattern) ---
def create_tools_demo():
    """Tools that agents can call - LangChain pattern."""
    from langchain_core.tools import tool

    @tool
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    @tool
    def multiply(a: int, b: int) -> int:
        """Multiply two numbers."""
        return a * b

    tools = [add, multiply]
    print(f"Tools: {[t.name for t in tools]}")
    return tools


# --- 5. Agent loop concept (observe → think → act) ---
def agent_loop_concept():
    """Simplified agent loop - no LLM, just the structure."""
    steps = ["observe", "think", "act", "observe", "think", "act", "done"]
    for i, step in enumerate(steps):
        print(f"  Step {i+1}: {step}")
    print("  (In real agents: LLM reasons, calls tools, observes results, repeats)")


if __name__ == "__main__":
    print("=== 1. Async + TypedDict ===\n")
    asyncio.run(main_async())

    print("\n=== 2. LangChain Messages ===\n")
    create_messages_demo()

    print("\n=== 3. LangChain Tools ===\n")
    create_tools_demo()

    print("\n=== 4. Agent Loop Concept ===\n")
    agent_loop_concept()
