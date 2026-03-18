# 06. Production

Deployment, observability, testing, and scaling.

---

## 1. Observability with LangSmith

- **Tracing** – See every node, edge, and state transition
- **Debugging** – Inspect inputs/outputs per step
- **Evaluation** – Run evals on datasets
- **Monitoring** – Latency, errors, token usage

**Setup:**

```bash
export LANGSMITH_TRACING=true
export LANGCHAIN_API_KEY=your_key
```

**LangSmith Studio** – Visualize and prototype graphs.

---

## 2. Deployment Options

| Option | Use case |
|--------|----------|
| **LangSmith Deployment** | Managed, scalable for LangGraph |
| **Self-hosted** | Docker, K8s, your infra |
| **Serverless** | Short-lived; checkpointing for long runs |
| **Custom API** | FastAPI/Flask wrapper around compiled graph |

**Considerations:**

- **Stateful** – Need persistent checkpointer (DB)
- **Concurrency** – Thread-safe checkpointer
- **Scaling** – Horizontal scaling with shared state store

---

## 3. Testing

- **Unit tests** – Test individual nodes with mock state
- **Integration tests** – Full graph with mocked LLM/tools
- **Evaluation** – Use LangSmith or custom evals on datasets
- **Regression** – Snapshot outputs for critical paths

**Pattern:**

```python
def test_node():
    state = {"messages": [HumanMessage(content="Hi")]}
    result = my_node(state)
    assert "messages" in result
    assert len(result["messages"]) == 1
```

---

## 4. Security

- **Input validation** – Sanitize user input
- **Tool permissions** – Limit what tools can do
- **Rate limiting** – Prevent abuse
- **Secrets** – Never log API keys; use env vars

---

## 5. Cost Optimization

- **Caching** – Cache LLM responses for repeated queries
- **Token limits** – Trim context, use smaller models where possible
- **Lazy tool loading** – Only load tools when needed
- **Batching** – Batch similar requests when applicable

---

## 6. Reliability

- **Retries** – For transient failures (API, network)
- **Circuit breakers** – Stop calling failing services
- **Graceful degradation** – Fallback when tools/APIs fail
- **Idempotency** – Safe retries for critical operations

---

## Checklist for Production

- [ ] LangSmith or equivalent tracing enabled
- [ ] Checkpointer configured (e.g., Postgres)
- [ ] Error handling and fallbacks
- [ ] Input validation
- [ ] Rate limiting and auth
- [ ] Monitoring and alerting
- [ ] Tests for critical paths
