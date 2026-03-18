# LangGraph: Path to Expert in AI Agentic Workflows

A structured learning roadmap for mastering LangGraph and building production-ready AI agentic workflows.

---

## Overview

**LangGraph** is a low-level orchestration framework for building stateful, long-running AI agents. Unlike linear chains, it uses a graph-based architecture with explicit control over nodes, edges, and shared state—enabling loops, branching, human-in-the-loop, and durable execution.

---

## Learning Path Structure

```
langgraph/
├── README.md                    # This file - roadmap overview
├── requirements.txt             # Dependencies
├── resources.md                 # Links, courses, docs
├── 01-prerequisites/             # Foundations before LangGraph
│   └── practice.py              # Async, TypedDict, messages, tools
├── 02-fundamentals/              # Core LangGraph concepts
│   └── practice.py              # StateGraph, nodes, conditional edges
├── 03-state-and-memory/          # State management & memory
│   └── practice.py              # MemorySaver, multi-turn, reducers
├── 04-agent-patterns/            # ReAct, tools, multi-agent
│   └── practice.py              # create_react_agent with tools
├── 05-advanced-features/         # Streaming, subgraphs, fallback
│   └── practice.py              # Streaming, subgraph, error handling
├── 06-production/               # Deployment, observability
│   └── practice.py              # Unit tests, FastAPI wrapper
└── 07-projects/                 # Hands-on projects
    ├── chatbot/                 # Simple chatbot with memory
    └── tool_agent/              # ReAct agent with tools
```

---

## Recommended Learning Order

| Phase | Topic | Est. Time |
|-------|-------|-----------|
| 1 | Prerequisites (Python, LLMs, LangChain basics) | 1–2 weeks |
| 2 | LangGraph fundamentals (StateGraph, nodes, edges) | 1 week |
| 3 | State & memory (MessagesState, checkpointing) | 1 week |
| 4 | Agent patterns (ReAct, tool use, multi-agent) | 2–3 weeks |
| 5 | Advanced features (interrupts, streaming, durable execution) | 1–2 weeks |
| 6 | Production (LangSmith, deployment, monitoring) | Ongoing |

---

## Quick Start

```bash
pip install -U langgraph langchain langchain-openai
```

```python
from langgraph.graph import StateGraph, MessagesState, START, END

def mock_llm(state: MessagesState):
    return {"messages": [{"role": "ai", "content": "hello world"}]}

graph = StateGraph(MessagesState)
graph.add_node(mock_llm)
graph.add_edge(START, "mock_llm")
graph.add_edge("mock_llm", END)
graph = graph.compile()

graph.invoke({"messages": [{"role": "user", "content": "hi!"}]})
```

---

## Key Concepts to Master

- **StateGraph** – Graph-based workflow definition
- **Nodes & Edges** – Building blocks and routing logic
- **State** – TypedDict/Pydantic shared context
- **Conditional edges** – Dynamic routing based on state
- **Checkpointing** – Persistence and resumability
- **Human-in-the-loop** – Interrupts and approvals
- **Streaming** – Token and event streaming
- **Durable execution** – Long-running, fault-tolerant agents

---

## Running Practice Code

```bash
pip install -r requirements.txt

# Run each section's practice (from langgraph/ root)
python 01-prerequisites/practice.py
python 02-fundamentals/practice.py
python 03-state-and-memory/practice.py
python 04-agent-patterns/practice.py   # Needs OPENAI_API_KEY for full demo
python 05-advanced-features/practice.py
python 06-production/practice.py

# Projects
python 07-projects/chatbot/main.py
python 07-projects/tool_agent/main.py  # Needs OPENAI_API_KEY
```

---

Navigate to each folder for detailed learning content and exercises.
