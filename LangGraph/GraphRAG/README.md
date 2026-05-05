# GraphRAG with NetworkX Knowledge Graph

A complete Graph RAG implementation that follows this 8-step architecture:

```
┌─────────────────────┐
│ 1. Query            │  LLM rewrites the question, extracts entities,
│    Understanding    │  generates paraphrases / sub-queries
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│ 2. NetworkX KG      │  Multi-hop walk over a typed knowledge graph
│    expansion        │  built from the documents (CAUSED_BY, PART_OF, ...)
└──────────┬──────────┘
           │   (parallel)
   ┌───────┴───────┬──────────────┬───────────┐
   ▼               ▼              ▼           ▼
┌────────┐   ┌──────────┐   ┌──────────┐  ┌────────┐
│Lexical │   │  BM25    │   │  Dense   │  │Graph   │
│Inverted│   │ rank_bm25│   │ Qdrant + │  │ hits   │
│ index  │   │          │   │ HF emb.  │  │        │
└────┬───┘   └─────┬────┘   └────┬─────┘  └───┬────┘
     │             │             │            │
     └────────┬────┴─────────────┴────────────┘
              │
   ┌──────────▼──────────┐
   │ 4. Reciprocal Rank  │  RRF fuses all 4 ranked lists
   │    Fusion           │
   └──────────┬──────────┘
              │
   ┌──────────▼──────────┐
   │ 5. Cross-Encoder    │  sentence-transformers MS-MARCO model
   │    Re-ranking       │
   └──────────┬──────────┘
              │
   ┌──────────▼──────────┐
   │ 6. Cause Ranking /  │  Combines KG causal proximity with text
   │    Retrieved        │  relevance over CAUSED_BY / SYMPTOM_OF /
   │    Evidence         │  MITIGATES edges
   └──────────┬──────────┘
              │
   ┌──────────▼──────────┐
   │ 7. Draft Procedure  │  LLM produces numbered step-by-step answer
   └──────────┬──────────┘
              │
   ┌──────────▼──────────┐
   │ 8. Self-Critic      │  LLM scores draft; loops back if score
   │    (loop)           │  < threshold (max_revisions in config)
   └──────────┬──────────┘
              ▼
          Final answer
```

Tech stack: **LangChain · LangGraph · LangSmith · NetworkX · Qdrant · BM25 · Cross-Encoder · Streamlit**.

## Layout

```
GraphRAG/
├── graph_rag_app.py     # entire pipeline + Streamlit UI in one file
├── config.yaml          # all knobs (models, top_k, weights, thresholds)
├── .env.example         # template for API keys + LangSmith
├── requirements.txt
├── data/                # drop your PDFs / Excel / JSON here
│   ├── sample_manual.json          # pump troubleshooting (JSON)
│   ├── sample_parts_catalog.xlsx   # spare-parts catalog (Excel, 2 sheets)
│   ├── sample_safety_manual.pdf    # LOTO / electrical safety (PDF)
│   └── _generate_samples.py        # regenerates the .xlsx and .pdf above
├── cache/               # local persistence (auto-created)
├── Dockerfile           # multi-stage build of the Streamlit app
├── docker-compose.yml   # full stack: graphrag + qdrant
├── .dockerignore
└── README.md
```

## Quick start

### Option A &mdash; Docker (recommended)

Brings up the Streamlit app **and** a real Qdrant server on a private network,
with persistent volumes for vectors and the HuggingFace model cache.

```bash
cd LangGraph/GraphRAG

cp .env.example .env
# edit .env: set OPENAI_API_KEY (and optionally LANGCHAIN_API_KEY)

docker compose up --build
```

- Streamlit UI: http://localhost:8501
- Qdrant dashboard: http://localhost:6333/dashboard

The compose file injects `QDRANT_URL=http://qdrant:6333`, so the app talks to
the Qdrant container instead of running it in-process. To stop:
`docker compose down` (add `-v` to also wipe the qdrant volume).

### Option B &mdash; Local virtualenv

```bash
cd LangGraph/GraphRAG

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env to add OPENAI_API_KEY (and optionally LANGCHAIN_API_KEY for LangSmith)

streamlit run graph_rag_app.py
```

Then in the UI:

1. **Ingest** tab → upload PDFs / Excel / JSON (or just use the bundled sample) → click **Build / Rebuild index**.
2. **Query** tab → type a question → click **Run pipeline**. The full step-by-step trace, all four retrieval lists, the cause-ranked evidence, and the self-critic JSON are all expandable.
3. **Knowledge Graph** tab → interactive graph view of the extracted KG, plus an edges table.

## Configuration

Everything pipeline-related is in `config.yaml`. The most useful knobs:

| Section | Key | What it controls |
| --- | --- | --- |
| `query_understanding.max_expansions` | int | Number of paraphrases the LLM emits per query |
| `knowledge_graph.builder` | `llm` / `heuristic` | LLM-extracted triples or regex pattern matching |
| `knowledge_graph.graph_expand_hops` | int | KG walk radius from query entities |
| `dense.embedding_model` | str | Any sentence-transformers model |
| `dense.qdrant.location` | `:memory:` or URL | Use a remote Qdrant by setting a URL |
| `rrf.k` | int | RRF damping constant (60 is the textbook default) |
| `reranker.model` | str | Cross-encoder used for the rerank step |
| `cause_ranking.weight_graph` / `weight_text` | float | Trade-off between KG proximity and text relevance |
| `self_critic.pass_threshold` | float | Score above which the draft is accepted |
| `self_critic.max_revisions` | int | Max loops back to the draft node |

## Notes on each step (where to find the code in `graph_rag_app.py`)

| # | Step | Function |
| --- | --- | --- |
| 1 | Query Understanding | `node_query_understanding` |
| 2 | NetworkX KG expansion | `build_knowledge_graph`, `node_graph_expand` |
| 3a | Lexical | `build_lexical_index`, `node_lexical` |
| 3b | BM25 | `build_bm25`, `node_bm25` |
| 3c | Dense (Qdrant) | `build_qdrant`, `node_dense` |
| 4 | Reciprocal Rank Fusion | `node_rrf` |
| 5 | Cross-Encoder Rerank | `node_rerank` |
| 6 | Cause Ranking / Evidence | `node_cause_ranking` |
| 7 | Draft Procedure | `node_draft` |
| 8 | Self-Critic (loop) | `node_self_critic`, `route_after_critic` |
| - | LangGraph wiring | `build_pipeline` |

## LangSmith tracing

Set these in `.env` and every node above is automatically traced (LangGraph + LangChain pick up the env vars):

```
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls_...
LANGCHAIN_PROJECT=GraphRAG-KG
```

## Running offline / without an OpenAI key

The code degrades gracefully:
- LLM calls fall back to a deterministic stub (you'll see `[stub LLM response]`).
- The KG builder falls back to the regex heuristic.
- The cross-encoder falls back to identity reranking.

So the retrieval, fusion, and KG halves of the pipeline work even with zero external services. Add the OpenAI key to enable the LLM-driven KG extraction, draft, and critic.

## Switching to a real Qdrant server

The cleanest option is `docker compose up` (see Quick start &mdash; Option A).
For a manual setup, either edit `config.yaml`:

```yaml
dense:
  qdrant:
    location: "http://localhost:6333"
```

or set the env var (which wins over `config.yaml`):

```bash
export QDRANT_URL=http://localhost:6333
# export QDRANT_API_KEY=...   # only if your Qdrant requires auth
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
streamlit run graph_rag_app.py
```
