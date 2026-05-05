"""
================================================================================
GraphRAG with NetworkX Knowledge Graph - single-file implementation
================================================================================

Architecture (matches the user spec, step-by-step):
    1. Query Understanding        - LLM expansion + entity extraction
    2. NetworkX Knowledge Graph   - typed relations, multi-hop expansion
    3. Lexical + BM25 + Dense     - 3 parallel retrievers (Qdrant for dense)
    4. Reciprocal Rank Fusion     - RRF combine of all 4 retrievers (incl. KG)
    5. Cross-Encoder Reranking    - sentence-transformers cross-encoder
    6. Cause Ranking / Evidence   - KG-walk over CAUSED_BY / SYMPTOM_OF edges
    7. Draft Procedure            - structured step-by-step answer
    8. Self-Critic                - LLM judge, loop back if score < threshold

Tech stack: LangChain, LangGraph, LangSmith, NetworkX, Qdrant, BM25, Streamlit.

Run:
    streamlit run graph_rag_app.py
"""

from __future__ import annotations

# =============================================================================
# 0. Imports & global setup
# =============================================================================
import os
import re
import json
import math
import uuid
import hashlib
import logging
import operator
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional, Tuple, TypedDict

import yaml
import numpy as np
import pandas as pd
import networkx as nx
import streamlit as st

from dotenv import load_dotenv

# LangChain / LangGraph / LangSmith ------------------------------------------
from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.runnables import RunnableLambda
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import StateGraph, START, END

# Retrieval ------------------------------------------------------------------
from rank_bm25 import BM25Okapi

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("graphrag")

ROOT = Path(__file__).parent.resolve()


# =============================================================================
# 1. Config loader
# =============================================================================
def load_config(path: str | Path = ROOT / "config.yaml") -> Dict[str, Any]:
    with open(path, "r") as f:
        cfg = yaml.safe_load(f)

    # Resolve relative paths against the project root
    proj = cfg.setdefault("project", {})
    for key in ("working_dir", "cache_dir", "data_dir"):
        if key in proj:
            proj[key] = str((ROOT / proj[key]).resolve())
    Path(proj["cache_dir"]).mkdir(parents=True, exist_ok=True)
    Path(proj["data_dir"]).mkdir(parents=True, exist_ok=True)

    # Wire LangSmith tracing from config + env
    ls = cfg.get("langsmith", {})
    if ls.get("enabled") and os.getenv("LANGCHAIN_API_KEY"):
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = ls.get("project", "GraphRAG-KG")
        os.environ.setdefault(
            "LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com"
        )
    return cfg


# =============================================================================
# 2. LLM and embedding factories (cached singletons)
# =============================================================================
def _stub_llm_invoke(prompt_value):
    """Deterministic offline stub - returns shape-correct payloads.

    Looks at the rendered prompt to decide which JSON / prose response to return.
    Keeps the app fully runnable without an API key.
    """
    text = (
        prompt_value.to_string()
        if hasattr(prompt_value, "to_string")
        else str(prompt_value)
    ).lower()
    if "triples" in text:
        return AIMessage(content='{"triples": []}')
    if '"score"' in text or ("score" in text and "draft" in text):
        return AIMessage(
            content='{"score": 1.0, "issues": [], "missing_evidence": []}'
        )
    if "entities" in text and "expansions" in text:
        return AIMessage(
            content='{"entities": [], "intent": "qa", "expansions": []}'
        )
    return AIMessage(
        content=(
            "1. Inspect the system using the cited evidence.\n"
            "2. Apply the recommended mitigation steps.\n"
            "3. Verify the issue is resolved.\n\n"
            "Caused by:\n- See retrieved evidence above."
        )
    )


@st.cache_resource(show_spinner=False)
def get_llm(model: str, temperature: float = 0.0):
    """Return a chat model. Falls back to a deterministic stub LLM offline."""
    try:
        from langchain_openai import ChatOpenAI

        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY missing - using stub LLM")
        return ChatOpenAI(model=model, temperature=temperature)
    except Exception as e:  # pragma: no cover
        log.warning("LLM unavailable (%s) - using stub LLM", e)
        return RunnableLambda(_stub_llm_invoke)


@st.cache_resource(show_spinner=False)
def get_embedder(model_name: str):
    from langchain_community.embeddings import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(model_name=model_name)


@st.cache_resource(show_spinner=False)
def get_cross_encoder(model_name: str):
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_name)


# =============================================================================
# 3. Document ingestion (PDF / Excel / JSON)
# =============================================================================
def _doc(text: str, source: str, **meta) -> Document:
    """Build a Document with a stable id."""
    cid = hashlib.md5(f"{source}:{text[:64]}:{uuid.uuid4()}".encode()).hexdigest()[:12]
    return Document(page_content=text, metadata={"id": cid, "source": source, **meta})


def load_pdf(path: Path) -> List[Document]:
    from pypdf import PdfReader

    docs: List[Document] = []
    reader = PdfReader(str(path))
    for i, page in enumerate(reader.pages):
        text = (page.extract_text() or "").strip()
        if text:
            docs.append(_doc(text, source=path.name, page=i + 1, type="pdf"))
    return docs


def load_excel(path: Path) -> List[Document]:
    """Each row becomes a document; concatenate column: value pairs."""
    docs: List[Document] = []
    xls = pd.ExcelFile(path)
    for sheet in xls.sheet_names:
        df = xls.parse(sheet).fillna("")
        for idx, row in df.iterrows():
            text = " | ".join(f"{c}: {row[c]}" for c in df.columns if str(row[c]).strip())
            if text:
                docs.append(
                    _doc(text, source=path.name, sheet=sheet, row=int(idx), type="excel")
                )
    return docs


def load_json(path: Path) -> List[Document]:
    """Recursively flatten dict / list JSON into per-leaf documents."""
    data = json.loads(path.read_text())
    docs: List[Document] = []

    def walk(node, trail: List[str]):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, trail + [str(k)])
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, trail + [f"[{i}]"])
        else:
            text = " > ".join(trail) + f": {node}"
            docs.append(_doc(text, source=path.name, path=" > ".join(trail), type="json"))

    walk(data, [])
    # Coalesce extremely small leaves with a sliding window so we get usable chunks
    if docs and all(len(d.page_content) < 80 for d in docs):
        merged: List[Document] = []
        buf: List[str] = []
        for d in docs:
            buf.append(d.page_content)
            if sum(map(len, buf)) > 600:
                merged.append(_doc("\n".join(buf), source=path.name, type="json"))
                buf = []
        if buf:
            merged.append(_doc("\n".join(buf), source=path.name, type="json"))
        return merged
    return docs


def ingest_directory(folder: Path) -> List[Document]:
    docs: List[Document] = []
    for p in folder.glob("**/*"):
        if p.is_dir():
            continue
        try:
            if p.suffix.lower() == ".pdf":
                docs.extend(load_pdf(p))
            elif p.suffix.lower() in (".xlsx", ".xls"):
                docs.extend(load_excel(p))
            elif p.suffix.lower() == ".json":
                docs.extend(load_json(p))
        except Exception as e:
            log.warning("Failed to load %s: %s", p, e)
    log.info("Loaded %d documents from %s", len(docs), folder)
    return docs


def chunk_documents(docs: List[Document], chunk_size: int, overlap: int) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    out: List[Document] = []
    for d in docs:
        for piece in splitter.split_text(d.page_content):
            out.append(_doc(piece, **{**d.metadata, "id": None}))
    # Re-issue ids so each chunk is unique
    for c in out:
        c.metadata["id"] = hashlib.md5(
            (c.metadata.get("source", "") + c.page_content[:64]).encode()
        ).hexdigest()[:12]
    return out


# =============================================================================
# 4. Knowledge Graph (NetworkX) construction
# =============================================================================
RELATION_VOCAB = [
    "CAUSED_BY", "PART_OF", "REQUIRES", "PRECEDES",
    "MITIGATES", "SYMPTOM_OF", "RELATED_TO",
]


def _heuristic_kg(chunks: List[Document], relation_types: List[str]) -> nx.MultiDiGraph:
    """Cheap fallback KG: scan text for 'X RELATION Y' patterns."""
    g = nx.MultiDiGraph()
    rel_pat = "|".join(re.escape(r) for r in relation_types)
    pattern = re.compile(
        rf"([A-Za-z][\w\s\-/]{{2,40}}?)\s+(?:is|are|was|were)?\s*({rel_pat})\s+([A-Za-z][\w\s\-/]{{2,60}})",
        re.IGNORECASE,
    )
    for ch in chunks:
        for m in pattern.finditer(ch.page_content):
            head = m.group(1).strip().lower()
            rel = m.group(2).strip().upper()
            tail = m.group(3).strip().lower().rstrip(".,;")
            g.add_node(head, label=head)
            g.add_node(tail, label=tail)
            g.add_edge(head, tail, relation=rel, chunk_id=ch.metadata["id"])
    return g


def _llm_kg(chunks: List[Document], relation_types: List[str], llm) -> nx.MultiDiGraph:
    """Ask the LLM to extract triples per chunk; merge into a MultiDiGraph."""
    g = nx.MultiDiGraph()

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an information extraction engine. Extract a list of "
                "(head, relation, tail) triples from the text. Only use these "
                "relation labels: {rels}. Return strict JSON: "
                '{{"triples":[{{"head":"...","relation":"...","tail":"..."}}]}}',
            ),
            ("human", "TEXT:\n{text}"),
        ]
    )
    chain = prompt | llm | JsonOutputParser()

    for ch in chunks:
        try:
            out = chain.invoke({"rels": ", ".join(relation_types), "text": ch.page_content})
            for t in out.get("triples", []):
                h = str(t.get("head", "")).strip().lower()
                r = str(t.get("relation", "")).strip().upper()
                ta = str(t.get("tail", "")).strip().lower()
                if h and r in relation_types and ta:
                    g.add_node(h, label=h)
                    g.add_node(ta, label=ta)
                    g.add_edge(h, ta, relation=r, chunk_id=ch.metadata["id"])
        except Exception as e:
            log.debug("KG extract skipped on chunk %s: %s", ch.metadata.get("id"), e)
    return g


def build_knowledge_graph(chunks: List[Document], cfg: Dict[str, Any]) -> nx.MultiDiGraph:
    kg_cfg = cfg["knowledge_graph"]
    rels = kg_cfg["relation_types"]
    if kg_cfg.get("builder", "heuristic") == "llm":
        try:
            llm = get_llm(kg_cfg["llm_model"], 0.0)
            g = _llm_kg(chunks, rels, llm)
            if g.number_of_edges() == 0:
                log.warning("LLM KG empty - falling back to heuristic")
                g = _heuristic_kg(chunks, rels)
        except Exception as e:
            log.warning("LLM KG builder failed (%s) - using heuristic", e)
            g = _heuristic_kg(chunks, rels)
    else:
        g = _heuristic_kg(chunks, rels)
    log.info("KG built: %d nodes, %d edges", g.number_of_nodes(), g.number_of_edges())
    return g


# =============================================================================
# 5. Indexers (lexical, BM25, dense Qdrant)
# =============================================================================
TOKEN = re.compile(r"[A-Za-z0-9_]+")


def tokenize(text: str) -> List[str]:
    return [t.lower() for t in TOKEN.findall(text)]


def build_lexical_index(chunks: List[Document]) -> Dict[str, Dict[str, int]]:
    """Inverted index: token -> {chunk_id: term frequency}."""
    inv: Dict[str, Dict[str, int]] = {}
    for ch in chunks:
        for tok in tokenize(ch.page_content):
            inv.setdefault(tok, {}).setdefault(ch.metadata["id"], 0)
            inv[tok][ch.metadata["id"]] += 1
    return inv


def build_bm25(chunks: List[Document]) -> BM25Okapi:
    return BM25Okapi([tokenize(c.page_content) for c in chunks])


def build_qdrant(chunks: List[Document], cfg: Dict[str, Any]):
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qm

    embedder = get_embedder(cfg["dense"]["embedding_model"])
    qcfg = cfg["dense"]["qdrant"]
    client = QdrantClient(location=qcfg["location"])
    collection = qcfg["collection"]
    dim = len(embedder.embed_query("dim probe"))

    distance = getattr(qm.Distance, qcfg.get("distance", "Cosine").upper())
    if client.collection_exists(collection):
        client.delete_collection(collection)
    client.create_collection(
        collection_name=collection,
        vectors_config=qm.VectorParams(size=dim, distance=distance),
    )

    vectors = embedder.embed_documents([c.page_content for c in chunks])
    points = [
        qm.PointStruct(
            id=str(uuid.uuid4()),
            vector=v,
            payload={
                "chunk_id": c.metadata["id"],
                "source": c.metadata.get("source"),
                "text": c.page_content,
            },
        )
        for c, v in zip(chunks, vectors)
    ]
    client.upsert(collection_name=collection, points=points)
    return client, collection, embedder


# =============================================================================
# 6. State definition for LangGraph
# =============================================================================
class GraphRAGState(TypedDict, total=False):
    query: str
    expanded: Dict[str, Any]            # {"entities": [...], "expansions": [...]}
    lexical: List[Dict[str, Any]]
    bm25: List[Dict[str, Any]]
    dense: List[Dict[str, Any]]
    graph_hits: List[Dict[str, Any]]
    fused: List[Dict[str, Any]]
    reranked: List[Dict[str, Any]]
    causes: List[Dict[str, Any]]
    draft: str
    critique: Dict[str, Any]
    final: str
    iteration: int
    # `trace` uses operator.add so parallel branches can each append entries
    trace: Annotated[List[Dict[str, Any]], operator.add]


def _t(step: str, payload: Any) -> List[Dict[str, Any]]:
    """Tiny helper - returns a single-entry list for the trace reducer."""
    return [{"step": step, "payload": payload}]


# =============================================================================
# 7. Pipeline node implementations
# =============================================================================
def node_query_understanding(state: GraphRAGState, ctx: Dict[str, Any]) -> Dict[str, Any]:
    cfg = ctx["cfg"]["query_understanding"]
    llm = get_llm(cfg["llm_model"], cfg["temperature"])

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You rewrite user questions for retrieval. "
                "Return strict JSON with: "
                '"entities" (key noun phrases, lowercase), '
                '"intent" (short label), '
                '"expansions" (up to {n} paraphrases / sub-queries).',
            ),
            ("human", "Question: {q}"),
        ]
    )
    try:
        out = (prompt | llm | JsonOutputParser()).invoke(
            {"q": state["query"], "n": cfg["max_expansions"]}
        )
    except Exception as e:
        log.warning("Query understanding fallback (%s)", e)
        out = {
            "entities": [t for t in tokenize(state["query"]) if len(t) > 3][:5],
            "intent": "qa",
            "expansions": [state["query"]],
        }

    out.setdefault("expansions", [])
    if state["query"] not in out["expansions"]:
        out["expansions"].insert(0, state["query"])
    if not out.get("entities"):
        out["entities"] = [t for t in tokenize(state["query"]) if len(t) > 3][:5]

    return {"expanded": out, "trace": _t("query_understanding", out)}


def node_graph_expand(state: GraphRAGState, ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Walk NetworkX from query entities; collect supporting chunk ids."""
    cfg = ctx["cfg"]["knowledge_graph"]
    g: nx.MultiDiGraph = ctx["kg"]
    hops = cfg["graph_expand_hops"]
    entities = [e.lower() for e in state["expanded"].get("entities", [])]
    seeds = [n for n in g.nodes if any(e in n for e in entities)] if entities else []

    chunk_scores: Dict[str, float] = {}
    edges_used: List[Tuple[str, str, str]] = []
    g_und = g.to_undirected(as_view=True)
    for seed in seeds:
        if seed not in g_und:
            continue
        dist_map = nx.single_source_shortest_path_length(g_und, seed, cutoff=hops)
        for node, dist in dist_map.items():
            for _, _, data in g.edges(node, data=True):
                cid = data.get("chunk_id")
                if cid:
                    chunk_scores[cid] = max(chunk_scores.get(cid, 0.0), 1.0 / (1 + dist))
                    edges_used.append((node, data.get("relation", "?"), seed))

    chunks = ctx["chunks_by_id"]
    hits = [
        {
            "chunk_id": cid,
            "score": s,
            "text": chunks[cid].page_content if cid in chunks else "",
            "source": chunks[cid].metadata.get("source") if cid in chunks else "",
        }
        for cid, s in sorted(chunk_scores.items(), key=lambda kv: -kv[1])
    ][: ctx["cfg"]["graph_retrieval"]["top_k"]]

    return {
        "graph_hits": hits,
        "trace": _t(
            "graph_expand",
            {"seeds": seeds, "edges": edges_used[:25], "hits": len(hits)},
        ),
    }


def node_lexical(state: GraphRAGState, ctx: Dict[str, Any]) -> Dict[str, Any]:
    cfg = ctx["cfg"]["lexical"]
    if not cfg.get("enabled", True):
        return {"lexical": [], "trace": _t("retrieve_lexical", {"skipped": True})}
    inv = ctx["lexical_index"]
    chunks = ctx["chunks_by_id"]

    scores: Dict[str, float] = {}
    queries = [state["query"]] + state["expanded"].get("expansions", [])
    for q in queries:
        for tok in tokenize(q):
            for cid, tf in inv.get(tok, {}).items():
                scores[cid] = scores.get(cid, 0.0) + tf
    hits = [
        {
            "chunk_id": cid,
            "score": float(s),
            "text": chunks[cid].page_content,
            "source": chunks[cid].metadata.get("source"),
        }
        for cid, s in sorted(scores.items(), key=lambda kv: -kv[1])[: cfg["top_k"]]
    ]
    return {"lexical": hits, "trace": _t("retrieve_lexical", {"hits": len(hits)})}


def node_bm25(state: GraphRAGState, ctx: Dict[str, Any]) -> Dict[str, Any]:
    cfg = ctx["cfg"]["bm25"]
    if not cfg.get("enabled", True):
        return {"bm25": [], "trace": _t("retrieve_bm25", {"skipped": True})}
    bm25: BM25Okapi = ctx["bm25"]
    chunks_list: List[Document] = ctx["chunks"]

    queries = [state["query"]] + state["expanded"].get("expansions", [])
    accum = np.zeros(len(chunks_list))
    for q in queries:
        accum += np.asarray(bm25.get_scores(tokenize(q)))
    top_idx = np.argsort(-accum)[: cfg["top_k"]]

    hits = []
    for i in top_idx:
        c = chunks_list[int(i)]
        hits.append(
            {
                "chunk_id": c.metadata["id"],
                "score": float(accum[int(i)]),
                "text": c.page_content,
                "source": c.metadata.get("source"),
            }
        )
    return {"bm25": hits, "trace": _t("retrieve_bm25", {"hits": len(hits)})}


def node_dense(state: GraphRAGState, ctx: Dict[str, Any]) -> Dict[str, Any]:
    cfg = ctx["cfg"]["dense"]
    if not cfg.get("enabled", True):
        return {"dense": [], "trace": _t("retrieve_dense", {"skipped": True})}
    client = ctx["qdrant_client"]
    collection = ctx["qdrant_collection"]
    embedder = ctx["embedder"]
    chunks = ctx["chunks_by_id"]

    queries = [state["query"]] + state["expanded"].get("expansions", [])
    pooled: Dict[str, float] = {}
    for q in queries:
        vec = embedder.embed_query(q)
        res = client.query_points(
            collection_name=collection, query=vec, limit=cfg["top_k"]
        )
        for r in res.points:
            cid = r.payload.get("chunk_id")
            pooled[cid] = max(pooled.get(cid, 0.0), float(r.score))
    hits = [
        {
            "chunk_id": cid,
            "score": s,
            "text": chunks[cid].page_content if cid in chunks else "",
            "source": chunks[cid].metadata.get("source") if cid in chunks else "",
        }
        for cid, s in sorted(pooled.items(), key=lambda kv: -kv[1])[: cfg["top_k"]]
    ]
    return {"dense": hits, "trace": _t("retrieve_dense", {"hits": len(hits)})}


def node_rrf(state: GraphRAGState, ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Reciprocal Rank Fusion over all 4 retrievers."""
    cfg = ctx["cfg"]["rrf"]
    k = cfg["k"]
    boards = {
        "lexical": state.get("lexical", []),
        "bm25": state.get("bm25", []),
        "dense": state.get("dense", []),
        "graph": state.get("graph_hits", []),
    }
    rrf: Dict[str, float] = {}
    contribs: Dict[str, Dict[str, int]] = {}
    for name, board in boards.items():
        for rank, hit in enumerate(board, start=1):
            cid = hit["chunk_id"]
            rrf[cid] = rrf.get(cid, 0.0) + 1.0 / (k + rank)
            contribs.setdefault(cid, {})[name] = rank

    chunks = ctx["chunks_by_id"]
    fused = [
        {
            "chunk_id": cid,
            "score": s,
            "contribs": contribs.get(cid, {}),
            "text": chunks[cid].page_content if cid in chunks else "",
            "source": chunks[cid].metadata.get("source") if cid in chunks else "",
        }
        for cid, s in sorted(rrf.items(), key=lambda kv: -kv[1])[: cfg["top_k_after_fusion"]]
    ]
    return {"fused": fused, "trace": _t("rrf_fusion", {"fused": len(fused)})}


def node_rerank(state: GraphRAGState, ctx: Dict[str, Any]) -> Dict[str, Any]:
    cfg = ctx["cfg"]["reranker"]
    fused = state.get("fused", [])
    if not cfg.get("enabled", True) or not fused:
        return {"reranked": fused, "trace": _t("cross_encoder_rerank", {"skipped": True})}
    try:
        ce = get_cross_encoder(cfg["model"])
        pairs = [(state["query"], h["text"]) for h in fused]
        ce_scores = ce.predict(pairs).tolist()
    except Exception as e:
        log.warning("Cross-encoder failed (%s) - keeping fused order", e)
        ce_scores = [h["score"] for h in fused]

    reranked = [{**h, "ce_score": float(s)} for h, s in zip(fused, ce_scores)]
    reranked.sort(key=lambda h: -h["ce_score"])
    reranked = reranked[: cfg["top_k_after_rerank"]]
    return {
        "reranked": reranked,
        "trace": _t("cross_encoder_rerank", {"top": len(reranked)}),
    }


def node_cause_ranking(state: GraphRAGState, ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Combine cross-encoder text relevance with KG causal proximity.

    For each top reranked chunk:
        cause_score = w_g * graph_proximity + w_t * normalised_text_score
    Graph proximity = 1/(1 + min hops) over `cause_relations` edges starting
    from any of the query entities.
    """
    cfg = ctx["cfg"]["cause_ranking"]
    reranked = state.get("reranked", [])

    if not cfg.get("enabled", True) or not reranked:
        causes = reranked[: cfg.get("top_k_causes", 5)]
        return {"causes": causes, "trace": _t("cause_ranking", {"top": len(causes)})}

    g: nx.MultiDiGraph = ctx["kg"]
    cause_rels = set(ctx["cfg"]["knowledge_graph"]["cause_relations"])
    entities = [e.lower() for e in state["expanded"].get("entities", [])]
    seeds = [n for n in g.nodes if any(e in n for e in entities)]

    sub = nx.MultiDiGraph(
        ((u, v, d) for u, v, d in g.edges(data=True) if d.get("relation") in cause_rels)
    )
    sub_u = sub.to_undirected(as_view=False)

    text_scores = np.array([h.get("ce_score", h.get("score", 0.0)) for h in reranked], dtype=float)
    if text_scores.max() != text_scores.min():
        text_norm = (text_scores - text_scores.min()) / (text_scores.max() - text_scores.min())
    else:
        text_norm = np.ones_like(text_scores)

    chunk_to_nodes: Dict[str, set] = {}
    for u, v, d in g.edges(data=True):
        cid = d.get("chunk_id")
        if cid:
            chunk_to_nodes.setdefault(cid, set()).update([u, v])

    causes: List[Dict[str, Any]] = []
    for h, t_norm in zip(reranked, text_norm):
        nodes = chunk_to_nodes.get(h["chunk_id"], set())
        best_hop = math.inf
        path: List[str] = []
        for s in seeds:
            if s not in sub_u:
                continue
            for n in nodes:
                if n in sub_u:
                    try:
                        hops = nx.shortest_path_length(sub_u, s, n)
                        if hops < best_hop:
                            best_hop = hops
                            path = nx.shortest_path(sub_u, s, n)
                    except nx.NetworkXNoPath:
                        continue
        graph_prox = 1.0 / (1.0 + best_hop) if math.isfinite(best_hop) else 0.0
        cause_score = cfg["weight_graph"] * graph_prox + cfg["weight_text"] * float(t_norm)
        causes.append(
            {
                **h,
                "graph_prox": graph_prox,
                "cause_path": path,
                "cause_score": cause_score,
            }
        )

    causes.sort(key=lambda x: -x["cause_score"])
    causes = causes[: cfg["top_k_causes"]]
    return {"causes": causes, "trace": _t("cause_ranking", {"top": len(causes)})}


def node_draft(state: GraphRAGState, ctx: Dict[str, Any]) -> Dict[str, Any]:
    cfg = ctx["cfg"]["draft"]
    llm = get_llm(cfg["llm_model"], cfg["temperature"])

    evidence_blocks = []
    for i, h in enumerate(state.get("causes", []) or state.get("reranked", []), start=1):
        path = " -> ".join(h.get("cause_path", [])) or "n/a"
        evidence_blocks.append(
            f"[E{i}] (source={h.get('source')}, cause_path={path})\n{h.get('text','')}"
        )
    evidence = "\n\n".join(evidence_blocks) or "(no evidence retrieved)"

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a senior field engineer. Using ONLY the evidence below, "
                "produce a numbered, step-by-step procedure (max {max_steps} steps) "
                "that answers the user's question. After the steps, list the most "
                'likely "Caused by" factors as a short bulleted section. '
                "Cite evidence inline as [E1], [E2], ... If evidence is insufficient, "
                "say so explicitly.",
            ),
            ("human", "QUESTION: {q}\n\nEVIDENCE:\n{evidence}"),
        ]
    )
    try:
        msg = (prompt | llm | StrOutputParser()).invoke(
            {"q": state["query"], "evidence": evidence, "max_steps": cfg["max_steps"]}
        )
    except Exception as e:
        log.warning("Draft fallback (%s)", e)
        msg = "1. Inspect the system per the manual.\n2. Consult evidence above.\n\nCaused by:\n- (see evidence)"
    return {"draft": msg, "trace": _t("draft_procedure", {"chars": len(msg)})}


def node_self_critic(state: GraphRAGState, ctx: Dict[str, Any]) -> Dict[str, Any]:
    cfg = ctx["cfg"]["self_critic"]
    iteration = state.get("iteration", 0) + 1

    if not cfg.get("enabled", True):
        review = {"score": 1.0, "passed": True, "issues": [], "missing_evidence": []}
        return {
            "iteration": iteration,
            "critique": review,
            "final": state["draft"],
            "trace": _t("self_critic", review),
        }

    llm = get_llm(cfg["llm_model"], cfg["temperature"])
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a strict reviewer. Score the DRAFT against the QUESTION and "
                "EVIDENCE on a 0-1 scale and list issues. Return strict JSON: "
                '{{"score":0..1,"issues":["..."],"missing_evidence":["..."]}}',
            ),
            ("human", "QUESTION:\n{q}\n\nDRAFT:\n{draft}\n\nEVIDENCE:\n{evidence}"),
        ]
    )
    evidence = (
        "\n\n".join(
            f"[E{i}] {h['text']}"
            for i, h in enumerate(state.get("causes", []) or state.get("reranked", []), start=1)
        )
        or "(none)"
    )

    try:
        review = (prompt | llm | JsonOutputParser()).invoke(
            {"q": state["query"], "draft": state["draft"], "evidence": evidence}
        )
    except Exception as e:
        log.warning("Self-critic fallback (%s)", e)
        review = {"score": 1.0, "issues": [], "missing_evidence": []}

    review["passed"] = float(review.get("score", 0.0)) >= cfg["pass_threshold"]
    out: Dict[str, Any] = {
        "iteration": iteration,
        "critique": review,
        "trace": _t("self_critic", review),
    }
    if review["passed"] or iteration > cfg["max_revisions"]:
        out["final"] = state["draft"]
    return out


def route_after_critic(state: GraphRAGState) -> str:
    """LangGraph conditional edge: redraft or finish."""
    if state.get("final"):
        return END
    return "draft"


# =============================================================================
# 8. LangGraph assembly
# =============================================================================
def build_pipeline(ctx: Dict[str, Any]):
    """ctx holds all index handles + cfg; nodes use ctx via closure."""
    g = StateGraph(GraphRAGState)

    g.add_node("query_understanding", lambda s: node_query_understanding(s, ctx))
    g.add_node("graph_expand", lambda s: node_graph_expand(s, ctx))
    g.add_node("retrieve_lexical", lambda s: node_lexical(s, ctx))
    g.add_node("retrieve_bm25", lambda s: node_bm25(s, ctx))
    g.add_node("retrieve_dense", lambda s: node_dense(s, ctx))
    g.add_node("rrf", lambda s: node_rrf(s, ctx))
    g.add_node("rerank", lambda s: node_rerank(s, ctx))
    g.add_node("cause_ranking", lambda s: node_cause_ranking(s, ctx))
    g.add_node("draft", lambda s: node_draft(s, ctx))
    g.add_node("self_critic", lambda s: node_self_critic(s, ctx))

    g.add_edge(START, "query_understanding")
    g.add_edge("query_understanding", "graph_expand")
    g.add_edge("query_understanding", "retrieve_lexical")
    g.add_edge("query_understanding", "retrieve_bm25")
    g.add_edge("query_understanding", "retrieve_dense")
    g.add_edge(["graph_expand", "retrieve_lexical", "retrieve_bm25", "retrieve_dense"], "rrf")
    g.add_edge("rrf", "rerank")
    g.add_edge("rerank", "cause_ranking")
    g.add_edge("cause_ranking", "draft")
    g.add_edge("draft", "self_critic")
    g.add_conditional_edges("self_critic", route_after_critic, {END: END, "draft": "draft"})

    return g.compile()


# =============================================================================
# 9. Index/context builder (Streamlit-cached)
# =============================================================================
def build_context(cfg: Dict[str, Any], data_dir: Path) -> Dict[str, Any]:
    raw = ingest_directory(data_dir)
    chunks = chunk_documents(raw, cfg["chunking"]["chunk_size"], cfg["chunking"]["chunk_overlap"])
    if not chunks:
        raise RuntimeError(f"No documents found in {data_dir}")
    chunks_by_id = {c.metadata["id"]: c for c in chunks}

    kg = build_knowledge_graph(chunks, cfg)
    lexical_index = build_lexical_index(chunks)
    bm25 = build_bm25(chunks)

    qdrant_client, qdrant_collection, embedder = build_qdrant(chunks, cfg)

    return {
        "cfg": cfg,
        "chunks": chunks,
        "chunks_by_id": chunks_by_id,
        "kg": kg,
        "lexical_index": lexical_index,
        "bm25": bm25,
        "qdrant_client": qdrant_client,
        "qdrant_collection": qdrant_collection,
        "embedder": embedder,
    }


# =============================================================================
# 10. Streamlit UI
# =============================================================================
def _render_kg(g: nx.MultiDiGraph, max_nodes: int = 80):
    """Render KG with streamlit-agraph (falls back to a table if unavailable)."""
    try:
        from streamlit_agraph import agraph, Node, Edge, Config
    except ImportError:
        st.dataframe(
            pd.DataFrame(
                [
                    {"head": u, "relation": d.get("relation"), "tail": v}
                    for u, v, d in g.edges(data=True)
                ]
            )
        )
        return

    nodes = list(g.nodes)[:max_nodes]
    node_set = set(nodes)
    a_nodes = [Node(id=n, label=n, size=18) for n in nodes]
    a_edges = [
        Edge(source=u, target=v, label=d.get("relation", ""))
        for u, v, d in g.edges(data=True)
        if u in node_set and v in node_set
    ]
    agraph(
        nodes=a_nodes,
        edges=a_edges,
        config=Config(width=900, height=550, directed=True, physics=True, hierarchical=False),
    )


def main():
    st.set_page_config(page_title="GraphRAG with NetworkX", layout="wide")
    st.title("GraphRAG - NetworkX KG + RRF + Cross-Encoder + Self-Critic")

    cfg = load_config()
    data_dir = Path(cfg["project"]["data_dir"])

    with st.sidebar:
        st.header("Configuration")
        st.code(yaml.safe_dump(cfg, sort_keys=False), language="yaml")
        st.markdown("**Drop your PDFs / Excel / JSON into**")
        st.code(str(data_dir))

    tab_ingest, tab_query, tab_kg = st.tabs(["1. Ingest", "2. Query", "3. Knowledge Graph"])

    # ---- Ingest tab --------------------------------------------------------
    with tab_ingest:
        st.subheader("Document ingestion")
        uploaded = st.file_uploader(
            "Upload extra files (saved into data/ before indexing)",
            type=["pdf", "xlsx", "xls", "json"],
            accept_multiple_files=True,
        )
        if uploaded:
            for f in uploaded:
                (data_dir / f.name).write_bytes(f.getbuffer())
            st.success(f"Saved {len(uploaded)} file(s) to {data_dir}")

        if st.button("Build / Rebuild index", type="primary"):
            with st.spinner("Loading, chunking, embedding, building KG..."):
                st.session_state["ctx"] = build_context(cfg, data_dir)
                st.session_state["pipeline"] = build_pipeline(st.session_state["ctx"])
            ctx = st.session_state["ctx"]
            st.success(
                f"Indexed {len(ctx['chunks'])} chunks. "
                f"KG: {ctx['kg'].number_of_nodes()} nodes / {ctx['kg'].number_of_edges()} edges."
            )

        if "ctx" in st.session_state:
            ctx = st.session_state["ctx"]
            st.metric("Chunks", len(ctx["chunks"]))
            c1, c2 = st.columns(2)
            c1.metric("KG nodes", ctx["kg"].number_of_nodes())
            c2.metric("KG edges", ctx["kg"].number_of_edges())

    # ---- Query tab ---------------------------------------------------------
    with tab_query:
        st.subheader("Ask a question")
        if "pipeline" not in st.session_state:
            st.info("Build the index in the **Ingest** tab first.")
        else:
            q = st.text_input(
                "Question",
                value="What can cause excessive vibration and how do I fix it?",
            )
            if st.button("Run pipeline", type="primary"):
                with st.spinner("Running 8-step GraphRAG pipeline..."):
                    state: GraphRAGState = {"query": q, "iteration": 0, "trace": []}
                    final_state = st.session_state["pipeline"].invoke(state)

                st.markdown("### Final answer")
                st.markdown(final_state.get("final") or final_state.get("draft", ""))

                with st.expander("Self-critic"):
                    st.json(final_state.get("critique", {}))

                with st.expander("Cause-ranked evidence"):
                    for i, c in enumerate(final_state.get("causes", []), start=1):
                        st.markdown(
                            f"**E{i}** | source=`{c.get('source')}` | "
                            f"cause_score=`{c.get('cause_score'):.3f}` | "
                            f"path=`{' -> '.join(c.get('cause_path', []))}`"
                        )
                        st.write(c.get("text", ""))
                        st.divider()

                with st.expander("Step-by-step trace"):
                    for entry in final_state.get("trace", []):
                        st.markdown(f"**{entry['step']}**")
                        st.json(entry["payload"])

                with st.expander("All retrievers (pre-fusion)"):
                    cols = st.columns(4)
                    for col, name in zip(cols, ["lexical", "bm25", "dense", "graph_hits"]):
                        col.markdown(f"**{name}**")
                        col.dataframe(
                            pd.DataFrame(final_state.get(name, []))[
                                [
                                    c
                                    for c in ("chunk_id", "score", "source")
                                    if c in (final_state.get(name, [{}])[0] if final_state.get(name) else {})
                                ]
                            ]
                            if final_state.get(name)
                            else pd.DataFrame()
                        )

    # ---- KG tab ------------------------------------------------------------
    with tab_kg:
        st.subheader("Knowledge graph")
        if "ctx" not in st.session_state:
            st.info("Build the index in the **Ingest** tab first.")
        else:
            _render_kg(st.session_state["ctx"]["kg"])
            with st.expander("Edges (table view)"):
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "head": u,
                                "relation": d.get("relation"),
                                "tail": v,
                                "chunk_id": d.get("chunk_id"),
                            }
                            for u, v, d in st.session_state["ctx"]["kg"].edges(data=True)
                        ]
                    )
                )


if __name__ == "__main__":
    main()
