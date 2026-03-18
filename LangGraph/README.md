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
├── 01-prerequisites/             # Foundations before LangGraph
├── 02-fundamentals/              # Core LangGraph concepts
├── 03-state-and-memory/          # State management & memory
├── 04-agent-patterns/            # ReAct, ReWOO, multi-agent, etc.
├── 05-advanced-features/         # Human-in-loop, checkpointing, streaming
├── 06-production/               # Deployment, observability, scaling
├── 07-projects/                 # Hands-on project ideas
└── resources.md                 # Links, courses, docs
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

Navigate to each folder for detailed learning content and exercises.
