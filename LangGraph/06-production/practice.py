"""
06. Production - Practice Code
Covers: Unit testing nodes, FastAPI wrapper, config.

Run: python practice.py
Run tests: pytest practice.py -v
"""

from typing import TypedDict

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END


# --- State ---
class ChatState(TypedDict):
    messages: list


# --- Node (production-style) ---
def chatbot_node(state: ChatState) -> dict:
    """Process user message and return AI response."""
    last = state["messages"][-1]
    content = getattr(last, "content", "") or ""
    reply = f"Echo: {content}"
    return {"messages": [AIMessage(content=reply)]}


# --- Unit test ---
def test_chatbot_node():
    """Unit test: verify node behavior with mock state."""
    state = {"messages": [HumanMessage(content="Hello")]}
    result = chatbot_node(state)
    assert "messages" in result
    assert len(result["messages"]) == 1
    assert "Echo:" in result["messages"][0].content
    assert "Hello" in result["messages"][0].content


# --- Build graph ---
def build_app():
    graph = StateGraph(ChatState)
    graph.add_node("chatbot", chatbot_node)
    graph.add_edge(START, "chatbot")
    graph.add_edge("chatbot", END)
    return graph.compile()


# --- FastAPI wrapper (optional, requires: pip install fastapi uvicorn) ---
def create_api():
    """Create FastAPI app wrapping the graph."""
    try:
        from fastapi import FastAPI
        from pydantic import BaseModel

        app = FastAPI(title="LangGraph Chat API")
        graph = build_app()

        class ChatRequest(BaseModel):
            message: str

        class ChatResponse(BaseModel):
            content: str

        @app.post("/chat", response_model=ChatResponse)
        def chat(req: ChatRequest):
            result = graph.invoke({
                "messages": [HumanMessage(content=req.message)],
            })
            last = result["messages"][-1]
            return ChatResponse(content=last.content)

        return app
    except ImportError:
        return None


if __name__ == "__main__":
    # Run unit test
    test_chatbot_node()
    print("Unit test passed.")

    # Run graph
    app = build_app()
    result = app.invoke({"messages": [HumanMessage(content="Test")]})
    print("Graph result:", result["messages"][-1].content)

    # API info
    api = create_api()
    if api:
        print("\nFastAPI app created. Run from 06-production/: uvicorn practice:create_api --factory")
    else:
        print("\nInstall fastapi, uvicorn for API: pip install fastapi uvicorn")
