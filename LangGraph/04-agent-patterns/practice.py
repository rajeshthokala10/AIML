"""
04. Agent Patterns - Practice Code
Covers: ReAct agent with tools, conditional tool loop.

Uses real LLM if OPENAI_API_KEY is set; otherwise runs with mock.
Run: python practice.py
"""

import os
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import create_react_agent


# --- Tools ---
@tool
def add(a: int, b: int) -> int:
    """Add two numbers. Use when user asks for sum or addition."""
    return a + b


@tool
def multiply(a: int, b: int) -> int:
    """Multiply two numbers. Use when user asks for product."""
    return a * b


@tool
def get_word_length(word: str) -> int:
    """Get the length of a word. Use when user asks for character count."""
    return len(word)


TOOLS = [add, multiply, get_word_length]


def build_react_agent():
    """Build ReAct agent using prebuilt create_react_agent."""
    if os.getenv("OPENAI_API_KEY"):
        model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        return create_react_agent(model, TOOLS)
    return None


def run_agent():
    """Run the ReAct agent with a math query."""
    agent = build_react_agent()
    if agent is None:
        print("Set OPENAI_API_KEY to run the real agent.")
        print("Example: OPENAI_API_KEY=sk-... python practice.py")
        print("\nTools defined:", [t.name for t in TOOLS])
        return

    print("=== ReAct Agent with Tools ===\n")
    result = agent.invoke({
        "messages": [HumanMessage(content="What is (3 + 5) * 2?")],
    })
    print("Final answer:", result["messages"][-1].content)


def run_agent_streaming():
    """Stream the agent response."""
    agent = build_react_agent()
    if agent is None:
        return

    print("\n=== Streaming ===\n")
    for chunk in agent.stream(
        {"messages": [HumanMessage(content="What is 10 + 7?")]},
        stream_mode="messages",
    ):
        for msg in chunk:
            if hasattr(msg, "content") and msg.content:
                print(msg.content, end="", flush=True)
    print()


if __name__ == "__main__":
    run_agent()
    run_agent_streaming()
