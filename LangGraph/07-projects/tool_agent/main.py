"""
07. Projects - Tool-Using Agent
ReAct agent with calculator and search tools.

Run: python main.py
Requires: OPENAI_API_KEY for real LLM
"""

import os
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent


@tool
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@tool
def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b


@tool
def search(query: str) -> str:
    """Search for information. (Mock - returns placeholder.)"""
    return f"[Mock search result for: {query}]"


TOOLS = [add, multiply, search]


def main():
    if not os.getenv("OPENAI_API_KEY"):
        print("Set OPENAI_API_KEY to run. Example: OPENAI_API_KEY=sk-... python main.py")
        return

    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    agent = create_react_agent(model, TOOLS)

    print("Tool Agent - Ask math or search questions (type 'quit' to exit)\n")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            break
        if not user_input:
            continue

        result = agent.invoke({"messages": [HumanMessage(content=user_input)]})
        print(f"Bot: {result['messages'][-1].content}\n")


if __name__ == "__main__":
    main()
