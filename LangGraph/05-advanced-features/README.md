# 05. Advanced Features

Human-in-the-loop, streaming, durable execution, and subgraphs.

---

## 1. Human-in-the-Loop (Interrupts)

Pause execution for human input or approval.

```python
from langgraph.types import interrupt

def approval_node(state):
    # Pause and wait for human input
    human_input = interrupt("Please approve this action")
    return {"approved": human_input}
```

**Use cases:**

- Approval workflows (e.g., financial transactions)
- Clarification requests
- Content moderation
- Escalation to human agent

**Resuming:** Call `invoke` with the human response; execution continues.

---

## 2. Streaming

**Token streaming** – Stream LLM tokens as they generate:

```python
for chunk in app.stream(input, stream_mode="values"):
    print(chunk["messages"][-1].content, end="")
```

**Stream modes:**

| Mode | What you get |
|------|--------------|
| `values` | Full state after each node |
| `updates` | State updates per node |
| `messages` | Message deltas |
| `custom` | Custom streamers |

**Async streaming:**

```python
async for chunk in app.astream_events(input):
    # Fine-grained events (token, node start/end, etc.)
    ...
```

---

## 3. Durable Execution

For long-running, fault-tolerant workflows:

- **Checkpointing** – State persisted at each step
- **Resume** – Continue after crash/restart
- **Timeouts** – Handle slow external APIs
- **Retries** – Configurable retry logic

**LangSmith Deployment** and similar platforms provide durable execution at scale.

---

## 4. Subgraphs

Compose graphs inside graphs for modularity:

```python
subgraph = StateGraph(SubState)
# ... build subgraph ...
sub_app = subgraph.compile()

def subgraph_node(state):
    result = sub_app.invoke(state)
    return result

main_graph.add_node("subgraph", subgraph_node)
```

**Use cases:** Reusable workflows, hierarchical agents, nested planning.

---

## 5. Parallel Nodes

Run multiple branches in parallel (where supported):

- **Send API** – Fan-out to multiple nodes
- **Gather** – Collect results before continuing

---

## 6. Timeouts and Cancellation

- Set **timeout** per node or globally
- **Cancel** long-running invocations
- Handle **partial completion** when interrupted

---

## 7. Validation and Error Handling

- **Input validation** – Pydantic models for state
- **Error nodes** – Catch exceptions, route to recovery
- **Fallbacks** – Alternative paths when nodes fail

---

## Exercises

1. Add an `interrupt` in a workflow and resume with user input
2. Stream tokens from an agent and display in real time
3. Build a parent graph that invokes a child subgraph
4. Implement error handling with a fallback node
