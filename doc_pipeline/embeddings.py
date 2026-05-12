"""
Embedding Pipeline — Sentence-transformer embeddings with FAISS vector index.

Handles encoding text chunks, building/saving/loading a FAISS index,
and performing similarity search with metadata retrieval.
"""

import json
import os
from pathlib import Path
from dataclasses import dataclass
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from chunking import Chunk


@dataclass
class SearchResult:
    text: str
    metadata: dict
    score: float
    chunk_id: int


class EmbeddingPipeline:
    """Encodes chunks with sentence-transformers and indexes them in FAISS."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2",
                 index_dir: str = "vector_store"):
        print(f"Loading embedding model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(exist_ok=True)
        self.index = None
        self.chunks: list[Chunk] = []
        self.embeddings: np.ndarray | None = None

    def build_index(self, chunks: list[Chunk], use_ivf: bool = True) -> None:
        """Encode all chunks and build a FAISS index."""
        self.chunks = chunks
        texts = [c.text for c in chunks]

        print(f"Encoding {len(texts)} chunks (dim={self.dimension})...")
        self.embeddings = self.model.encode(
            texts, show_progress_bar=True, batch_size=64,
            normalize_embeddings=True
        )
        self.embeddings = np.array(self.embeddings, dtype=np.float32)

        if use_ivf and len(chunks) > 100:
            n_clusters = min(int(np.sqrt(len(chunks))), 64)
            quantizer = faiss.IndexFlatIP(self.dimension)
            self.index = faiss.IndexIVFFlat(quantizer, self.dimension, n_clusters,
                                            faiss.METRIC_INNER_PRODUCT)
            self.index.train(self.embeddings)
            self.index.add(self.embeddings)
            self.index.nprobe = min(n_clusters, 10)
            print(f"Built IVF index with {n_clusters} clusters, nprobe={self.index.nprobe}")
        else:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.index.add(self.embeddings)
            print(f"Built flat index with {self.index.ntotal} vectors")

    def search(self, query: str, top_k: int = 5,
               score_threshold: float = 0.0) -> list[SearchResult]:
        """Search the index for chunks most similar to the query."""
        if self.index is None:
            raise RuntimeError("Index not built. Call build_index() first.")

        query_embedding = self.model.encode(
            [query], normalize_embeddings=True
        ).astype(np.float32)

        scores, indices = self.index.search(query_embedding, min(top_k * 2, self.index.ntotal))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.chunks):
                continue
            if score < score_threshold:
                continue
            chunk = self.chunks[idx]
            results.append(SearchResult(
                text=chunk.text,
                metadata=chunk.metadata,
                score=float(score),
                chunk_id=chunk.chunk_id,
            ))
            if len(results) >= top_k:
                break

        return results

    def search_with_context(self, query: str, top_k: int = 5,
                            context_window: int = 1) -> list[SearchResult]:
        """Search and include neighboring chunks for broader context."""
        base_results = self.search(query, top_k=top_k)
        if context_window == 0:
            return base_results

        expanded = []
        seen_ids = set()
        for result in base_results:
            cid = result.chunk_id
            for offset in range(-context_window, context_window + 1):
                neighbor_id = cid + offset
                if 0 <= neighbor_id < len(self.chunks) and neighbor_id not in seen_ids:
                    seen_ids.add(neighbor_id)
                    chunk = self.chunks[neighbor_id]
                    if chunk.metadata.get("source") == result.metadata.get("source"):
                        expanded.append(SearchResult(
                            text=chunk.text,
                            metadata=chunk.metadata,
                            score=result.score if offset == 0 else result.score * 0.8,
                            chunk_id=neighbor_id,
                        ))

        expanded.sort(key=lambda r: r.score, reverse=True)
        return expanded[:top_k + context_window * 2]

    def save(self, name: str = "manufacturing_index") -> None:
        """Persist index, embeddings, and chunk metadata to disk."""
        faiss.write_index(self.index, str(self.index_dir / f"{name}.faiss"))
        np.save(str(self.index_dir / f"{name}_embeddings.npy"), self.embeddings)

        chunk_data = [{
            "text": c.text, "metadata": c.metadata,
            "chunk_id": c.chunk_id, "strategy": c.strategy
        } for c in self.chunks]
        with open(self.index_dir / f"{name}_chunks.json", "w") as f:
            json.dump(chunk_data, f, indent=2, default=str)

        print(f"Saved index to {self.index_dir / name}.*")

    def load(self, name: str = "manufacturing_index") -> None:
        """Load a previously saved index from disk."""
        self.index = faiss.read_index(str(self.index_dir / f"{name}.faiss"))
        self.embeddings = np.load(str(self.index_dir / f"{name}_embeddings.npy"))

        with open(self.index_dir / f"{name}_chunks.json") as f:
            chunk_data = json.load(f)

        self.chunks = [
            Chunk(text=c["text"], metadata=c["metadata"],
                  chunk_id=c["chunk_id"], strategy=c["strategy"])
            for c in chunk_data
        ]
        print(f"Loaded index: {self.index.ntotal} vectors, {len(self.chunks)} chunks")

    def get_model(self) -> SentenceTransformer:
        """Return the underlying sentence-transformer model (used by semantic chunker)."""
        return self.model
