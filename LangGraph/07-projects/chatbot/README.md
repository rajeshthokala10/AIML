# Chatbot Project

A simple chatbot with optional memory and LLM.

## Run

```bash
# With mock (no API key)
python main.py

# With real LLM
export OPENAI_API_KEY=sk-...
python main.py
```

## Features

- Linear graph: user → LLM → response
- MemorySaver for multi-turn conversation
- Mock fallback when no API key
