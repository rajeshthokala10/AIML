# LangGraph: Resources & References

---

## Official Links

- **Docs:** https://langchain-ai.github.io/langgraph/
- **LangChain Docs:** https://docs.langchain.com/
- **GitHub:** https://github.com/langchain-ai/langgraph
- **LangSmith:** https://smith.langchain.com/

---

## Courses & Tutorials

- **LangChain Academy** – "Introduction to LangGraph" (free)
- **Coursera** – "Agentic AI with LangChain and LangGraph"
- **LangGraph YouTube** – Official tutorials and examples

---

## Key Documentation Pages

- StateGraph, nodes, edges
- MessagesState
- Checkpointing
- Human-in-the-loop (interrupts)
- Streaming
- Prebuilt agents (`create_react_agent`)
- Deployment

---

## Community

- **LangChain Discord** – #langgraph channel
- **GitHub Discussions** – LangGraph repo
- **LangChain Blog** – Announcements and guides

---

## Related Concepts

- **Pregel** – Google's graph processing model (inspiration)
- **NetworkX** – Graph API inspiration
- **Apache Beam** – Dataflow inspiration

---

## Books & Articles

- "Building AI Agents with LangGraph" – Step-by-step guides
- LangChain blog posts on agent architectures

---

## Quick Reference

| Task | Import / API |
|------|--------------|
| StateGraph | `from langgraph.graph import StateGraph, START, END` |
| MessagesState | `from langgraph.graph import MessagesState` |
| Create ReAct agent | `from langgraph.prebuilt import create_react_agent` |
| Memory checkpointer | `from langgraph.checkpoint.memory import MemorySaver` |
| Interrupt | `from langgraph.types import interrupt` |
