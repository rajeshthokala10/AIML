# 02. LangGraph Fundamentals

Core building blocks: StateGraph, nodes, and edges.

---

## 1. StateGraph

The main abstraction. A graph where:

- **State** flows through nodes
- **Nodes** are functions that read and update state
- **Edges** define transitions (unconditional or conditional)

```python
from langgraph.graph import StateGraph, MessagesState, START, END

graph = StateGraph(MessagesState)
```

---

## 2. State

Shared context across all nodes. Typically a `TypedDict` or Pydantic model.

**MessagesState** (built-in):

```python
from langgraph.graph import MessagesState

# MessagesState has: messages: list[BaseMessage]
# Nodes return partial updates that get merged
```

**Custom state:**

```python
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class MyState(TypedDict):
    messages: Annotated[list, add_messages]  # Reducer for append
    count: int
    metadata: dict
```

**Reducers:** Control how updates merge (e.g., `add_messages` appends, default replaces).

---

## 3. Nodes

Functions that receive state and return a state update (partial dict).

```python
def my_node(state: MessagesState):
    # state["messages"] contains current messages
    return {"messages": [AIMessage(content="Response")]}
```

- Nodes are **pure** in spirit: given state in, produce update out
- Return only the keys you want to update
- State is merged automatically using reducers

---

## 4. Edges

**Unconditional edges** – Always go to the next node:

```python
graph.add_edge(START, "node_a")
graph.add_edge("node_a", "node_b")
graph.add_edge("node_b", END)
```

**Conditional edges** – Route based on state:

```python
def route_after_llm(state):
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return "end"

graph.add_conditional_edges("llm", route_after_llm, {"tools": "tools", "end": END})
```

---

## 5. Compile & Run

```python
app = graph.compile()

# Synchronous
result = app.invoke({"messages": [HumanMessage(content="Hi")]})

# Async
result = await app.ainvoke({"messages": [HumanMessage(content="Hi")]})

# Stream
for chunk in app.stream({"messages": [...]}):
    print(chunk)
```

---

## Key Takeaways

| Concept | Purpose |
|---------|---------|
| StateGraph | Define workflow as a graph |
| State | Shared, typed context |
| Nodes | Process and update state |
| Edges | Unconditional or conditional routing |
| Compile | Turn graph into runnable app |

---

## Exercises

1. Build a linear graph: START → node_a → node_b → END
2. Add a conditional edge that branches based on message length
3. Create a custom state with a counter that increments in each node
