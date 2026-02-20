"""
RAG at inference: retrieve similar (question, gold_sql) examples and use as few-shot context.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

# Lazy-load sentence_transformers to avoid import cost when RAG is disabled
_embedder = None
_embeddings_cache = None
_examples_cache = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedder = SentenceTransformer("all-MiniLM-L6-v2")
        except ImportError:
            raise ImportError(
                "RAG requires sentence-transformers. Install with: pip install sentence-transformers"
            )
    return _embedder


def load_examples(examples_path: str) -> List[dict]:
    """Load (question, gold_sql) pairs from a JSONL file."""
    path = Path(examples_path)
    if not path.exists():
        return []
    examples = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if "question" in obj and "gold_sql" in obj:
                examples.append({"question": obj["question"], "gold_sql": obj["gold_sql"]})
    return examples


def get_embeddings_and_examples(examples_path: str):
    """Load examples and compute embeddings; cache by path."""
    global _embeddings_cache, _examples_cache
    cache_key = str(Path(examples_path).resolve())
    if _embeddings_cache is not None and _examples_cache is not None:
        # Single path cache for typical use (one train file)
        if hasattr(get_embeddings_and_examples, "_last_path") and get_embeddings_and_examples._last_path == cache_key:
            return _embeddings_cache, _examples_cache
    examples = load_examples(examples_path)
    if not examples:
        return [], []
    embedder = _get_embedder()
    questions = [ex["question"] for ex in examples]
    embeddings = embedder.encode(questions, normalize_embeddings=True)
    get_embeddings_and_examples._last_path = cache_key
    _embeddings_cache = embeddings
    _examples_cache = examples
    return embeddings, examples


def get_similar_examples(
    question: str,
    examples_path: str,
    top_k: int = 3,
) -> List[dict]:
    """
    Return top-k (question, gold_sql) examples most similar to the given question.
    examples_path: path to JSONL with "question" and "gold_sql" (e.g. train_employee.jsonl).
    """
    embeddings, examples = get_embeddings_and_examples(examples_path)
    if not examples:
        return []
    embedder = _get_embedder()
    q_emb = embedder.encode([question], normalize_embeddings=True)
    # Cosine similarity (both sides normalized)
    from numpy import dot
    sims = dot(embeddings, q_emb.T).ravel()
    indices = sims.argsort()[::-1][:top_k]
    return [examples[i] for i in indices]


def build_few_shot_prompt(schema_prompt: str, question: str, similar_examples: List[dict]) -> str:
    """
    Build prompt: a few "query for: Q -> SQL" lines, then the usual "tables: ... query for: question".
    """
    parts = []
    for ex in similar_examples:
        parts.append(f"query for: {ex['question']}\n{ex['gold_sql']}\n")
    parts.append("tables:\n")
    parts.append(schema_prompt)
    parts.append("\n")
    parts.append(f"query for: {question}\n")
    return "".join(parts)
