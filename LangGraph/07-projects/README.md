# 07. Practice Projects

Hands-on projects to solidify your LangGraph skills.

---

## Beginner

### 1. Simple Chatbot
- Linear graph: user → LLM → response
- Add `MessagesState` and basic streaming
- **Goal:** Understand nodes, edges, invoke/stream

### 2. Tool-Using Agent
- One LLM node + one tools node
- 2–3 tools (e.g., calculator, weather, search)
- Conditional edge: tool_calls → tools, else → END
- **Goal:** ReAct loop from scratch

### 3. Conversational Memory
- Add `MemorySaver` checkpointer
- Multi-turn conversation with `thread_id`
- **Goal:** Stateful, resumable chats

---

## Intermediate

### 4. Research Assistant
- Agent with tools: web search, Wikipedia, summarization
- Multi-step research with synthesis
- **Goal:** Complex tool orchestration

### 5. Agentic RAG
- Document ingestion + vector store
- Agent that decides what to retrieve
- Iterative retrieval and synthesis
- **Goal:** Beyond fixed RAG

### 6. Approval Workflow
- Agent proposes action
- `interrupt` for human approval
- Resume with approve/reject
- **Goal:** Human-in-the-loop

---

## Advanced

### 7. Multi-Agent System
- Supervisor + 3 specialists (researcher, coder, writer)
- Supervisor routes based on task type
- Aggregator combines outputs
- **Goal:** Multi-agent coordination

### 8. Plan-and-Execute Agent
- Planner breaks task into steps
- Executor runs each step with tools
- Replanner on failure
- **Goal:** Long-horizon planning

### 9. Production-Ready Agent
- LangSmith tracing
- Postgres checkpointer
- FastAPI wrapper
- Error handling, retries, rate limiting
- **Goal:** Deploy-ready system

---

## Included Practice Projects

| Project | Path | Level |
|---------|------|-------|
| Chatbot | `chatbot/main.py` | Beginner |
| Tool Agent | `tool_agent/main.py` | Intermediate |

## Project Template

```python
# langgraph/07-projects/your_project/
# ├── main.py
# ├── graph.py
# ├── tools.py
# ├── requirements.txt
# └── README.md
```

Start with `main.py` and `graph.py`; add tools and state as needed.
