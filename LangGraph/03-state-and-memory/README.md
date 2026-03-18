# 03. State and Memory

State management, checkpointing, and memory for stateful agents.

---

## 1. State Design

**Principles:**

- Keep state **minimal** – Only what nodes need
- Use **reducers** for list/dict fields that should merge, not replace
- Prefer **immutable** updates – Return new values, don't mutate in place

**Common patterns:**

```python
from typing import Annotated
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]  # Append messages
    current_step: str
    context: dict  # Replaced on update
```

---

## 2. Checkpointing

Enables:

- **Persistence** – Save state to DB
- **Resumability** – Resume after crash or pause
- **Time travel** – Inspect past states
- **Branching** – Fork from a checkpoint

```python
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
app = graph.compile(checkpointer=memory)

config = {"configurable": {"thread_id": "user-123"}}
result = app.invoke(input, config)

# Resume later with same thread_id
result = app.invoke(None, config)  # Continues from last state
```

**Checkpointer types:** `MemorySaver`, `SqliteSaver`, Postgres, etc.

---

## 3. Short-term Memory (Conversation)

- **MessagesState** – Stores conversation history
- **add_messages** – Appends new messages, handles tool calls
- **Trimming** – Limit context window size for long conversations

```python
from langgraph.prebuilt import create_react_agent
# Prebuilt agents handle message trimming
```

---

## 4. Long-term Memory

For cross-session persistence:

- **Vector stores** – Store embeddings, retrieve by similarity
- **Entity stores** – Store facts about users/entities
- **Custom state** – Persist via checkpointer + external DB

**Pattern:** Node that reads from vector store, injects into state before LLM.

---

## 5. State Reducers

Control how updates merge:

| Reducer | Behavior |
|---------|----------|
| (default) | Replace value |
| `add_messages` | Append messages, merge tool calls |
| Custom reducer | Your merge logic |

```python
def merge_lists(left, right):
    return left + right

class State(TypedDict):
    items: Annotated[list, merge_lists]
```

---

## Exercises

1. Add `MemorySaver` to a graph and run multiple invokes with the same `thread_id`
2. Implement a custom reducer that keeps only the last N messages
3. Build a node that fetches from a vector store and adds results to state
