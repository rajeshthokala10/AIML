# 04. Agent Patterns

ReAct, tool use, multi-agent, and agentic RAG.

---

## 1. ReAct (Reasoning + Acting)

Classic agent loop:

1. **Reason** – LLM thinks about next step
2. **Act** – Call tools based on reasoning
3. **Observe** – Get tool results, add to context
4. **Repeat** – Until task is done or max iterations

**LangGraph implementation:**

```
START → agent (LLM) → conditional: tool_calls? → tools → agent → ...
                              ↓ no
                            END
```

```python
from langgraph.prebuilt import create_react_agent

agent = create_react_agent(model, tools)
agent.invoke({"messages": [HumanMessage(content="What's the weather?")]})
```

---

## 2. Tool Use

- Define tools with `@tool` or `StructuredTool`
- LLM decides when to call tools
- Tool results are added to messages
- Loop until LLM produces final answer (no more tool calls)

**Best practices:**

- Clear tool names and descriptions
- Handle tool errors gracefully
- Limit tool call depth to avoid infinite loops

---

## 3. Multi-Agent Systems

Multiple specialized agents collaborating:

- **Supervisor** – Routes to specialist agents
- **Specialists** – Each has specific tools/domain
- **Debate/consensus** – Agents argue and converge

**Pattern:**

```
                    ┌→ researcher →
supervisor (router) ─┼→ coder      →  aggregator → END
                    └→ writer     →
```

**Key concepts:**

- Shared or separate state per agent
- Inter-agent messaging
- Handoff nodes for agent transitions

---

## 4. Agentic RAG

RAG with an agent loop instead of fixed retrieval:

1. Agent decides **what** to retrieve
2. Multiple retrieval steps if needed
3. Synthesis over retrieved chunks
4. Can use tools: search, vector store, web scrape

**vs traditional RAG:** More flexible, handles multi-hop and iterative retrieval.

---

## 5. Reflection / Self-Critique

Agent evaluates its own output and retries:

```
generate → critique → conditional: good? → END
                            ↓ no
                         generate (retry)
```

Useful for code generation, writing, and complex reasoning.

---

## 6. Plan-and-Execute

1. **Planner** – Breaks task into steps
2. **Executor** – Runs each step (possibly with tools)
3. **Replanner** – Adjusts plan if steps fail

Better for long-horizon tasks than pure ReAct.

---

## Exercises

1. Build a ReAct agent from scratch (no `create_react_agent`)
2. Create a supervisor + 2 specialist agents
3. Implement agentic RAG with a retrieval tool
4. Add a reflection node that triggers retry if quality is low
