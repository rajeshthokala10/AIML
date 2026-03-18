# 01. Prerequisites

Build a solid foundation before diving into LangGraph.

---

## 1. Python (Intermediate)

- **Async/await** – LangGraph supports async for streaming and concurrency
- **TypedDict & Pydantic** – Used for state schemas
- **Type hints** – Essential for state and node signatures
- **Context managers** – For resource handling in long-running workflows

**Practice:** Write a small async script with TypedDict state.

---

## 2. LLM Fundamentals

- How **prompts** and **completions** work
- **Tokenization** and context windows
- **Temperature**, top_p, and sampling
- **Function/tool calling** – Structured outputs for agent tools
- **Embeddings** – For RAG and semantic search

**Resources:** OpenAI API docs, Anthropic docs, or any LLM provider you use.

---

## 3. LangChain Basics (Recommended)

LangGraph often uses LangChain components. Learn:

- **LCEL (LangChain Expression Language)** – Composable chains
- **Models** – `ChatOpenAI`, `ChatAnthropic`, etc.
- **Messages** – `HumanMessage`, `AIMessage`, `SystemMessage`
- **Tools** – Defining and using tools with `@tool` decorator
- **Runnable** – `invoke`, `stream`, `batch`

**Note:** LangGraph can be used without LangChain, but LangChain simplifies model and tool integration.

---

## 4. Agent Concepts

- **Agents vs chains** – Agents use tools and can loop
- **ReAct** – Reasoning + Acting pattern
- **Tool use** – When and how LLMs call external functions
- **Orchestration** – Coordinating multiple steps and tools

---

## 5. Graph Thinking

- **Nodes** – Discrete processing steps
- **Edges** – Transitions between steps
- **Conditional routing** – Branching based on output
- **Cycles** – Loops for iterative reasoning

---

## Checklist Before LangGraph

- [ ] Comfortable with Python async and type hints
- [ ] Understand LLM APIs and tool calling
- [ ] Can build a simple LangChain chain with tools
- [ ] Understand the agent loop (observe → think → act → repeat)
