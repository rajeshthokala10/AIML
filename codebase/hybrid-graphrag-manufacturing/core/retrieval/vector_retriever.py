import re
import numpy as np
from typing import List, Dict, Optional, Set
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    import chromadb
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False

from config import CHROMA_DIR, CHROMA_COLLECTION


class VectorRetriever:
    def __init__(self):
        self._documents: List[Dict] = []
        self._use_chromadb = HAS_CHROMADB
        self._collection = None
        self._client = None
        self._tfidf_matrix = None
        self._vectorizer = None

    def build_index(self, documents: List[Dict]) -> None:
        self._documents = documents

        if self._use_chromadb:
            try:
                self._build_chromadb_index(documents)
                return
            except Exception as e:
                print(f"  ChromaDB failed ({e}), falling back to TF-IDF vectors")
                self._use_chromadb = False

        self._build_tfidf_index(documents)

    def _build_chromadb_index(self, documents: List[Dict]) -> None:
        self._client = chromadb.Client()
        try:
            self._client.delete_collection(CHROMA_COLLECTION)
        except Exception:
            pass

        self._collection = self._client.create_collection(
            name=CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"}
        )

        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            self._collection.add(
                ids=[doc["chunk_id"] for doc in batch],
                documents=[doc["text"] for doc in batch],
                metadatas=[{k: str(v) for k, v in doc.get("metadata", {}).items()} for doc in batch],
            )

    def _build_tfidf_index(self, documents: List[Dict]) -> None:
        corpus = [doc["text"] for doc in documents]
        self._vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        self._tfidf_matrix = self._vectorizer.fit_transform(corpus)

    def retrieve(self, query: str, top_k: int = 10, allow_list: Optional[Set[str]] = None) -> List[Dict]:
        if self._use_chromadb and self._collection:
            return self._retrieve_chromadb(query, top_k, allow_list)
        return self._retrieve_tfidf(query, top_k, allow_list)

    def _retrieve_chromadb(self, query: str, top_k: int, allow_list: Optional[Set[str]]) -> List[Dict]:
        fetch_k = top_k * 3 if allow_list else top_k

        results = self._collection.query(
            query_texts=[query],
            n_results=min(fetch_k, self._collection.count()),
        )

        scored_docs = []
        if results and results["ids"]:
            for i, chunk_id in enumerate(results["ids"][0]):
                if allow_list and chunk_id not in allow_list:
                    continue

                distance = results["distances"][0][i] if results.get("distances") else 0
                similarity = 1.0 - distance

                scored_docs.append({
                    "chunk_id": chunk_id,
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                    "vector_score": float(similarity),
                })

        scored_docs.sort(key=lambda x: x["vector_score"], reverse=True)
        return scored_docs[:top_k]

    def _retrieve_tfidf(self, query: str, top_k: int, allow_list: Optional[Set[str]]) -> List[Dict]:
        if self._vectorizer is None or self._tfidf_matrix is None:
            return []

        query_vec = self._vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self._tfidf_matrix).flatten()

        scored_docs = []
        for i, score in enumerate(similarities):
            doc = self._documents[i]
            if allow_list and doc["chunk_id"] not in allow_list:
                continue
            scored_docs.append({
                "chunk_id": doc["chunk_id"],
                "text": doc["text"],
                "metadata": doc.get("metadata", {}),
                "vector_score": float(score),
            })

        scored_docs.sort(key=lambda x: x["vector_score"], reverse=True)
        return scored_docs[:top_k]
