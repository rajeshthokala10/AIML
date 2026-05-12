import re
import math
from typing import List, Dict, Optional, Set
from collections import Counter

try:
    from rank_bm25 import BM25Okapi
    HAS_BM25 = True
except ImportError:
    HAS_BM25 = False


class SimpleBM25:
    """Minimal BM25 implementation as fallback when rank_bm25 is not installed."""

    def __init__(self, corpus: List[List[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus = corpus
        self.doc_len = [len(doc) for doc in corpus]
        self.avgdl = sum(self.doc_len) / len(corpus) if corpus else 1
        self.n_docs = len(corpus)
        self.df = {}
        for doc in corpus:
            seen = set()
            for term in doc:
                if term not in seen:
                    self.df[term] = self.df.get(term, 0) + 1
                    seen.add(term)
        self.tf = [Counter(doc) for doc in corpus]

    def get_scores(self, query: List[str]) -> List[float]:
        scores = []
        for i in range(self.n_docs):
            score = 0.0
            dl = self.doc_len[i]
            for term in query:
                if term not in self.df:
                    continue
                tf = self.tf[i].get(term, 0)
                idf = math.log((self.n_docs - self.df[term] + 0.5) / (self.df[term] + 0.5) + 1)
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
                score += idf * numerator / denominator
            scores.append(score)
        return scores


class BM25Retriever:
    def __init__(self):
        self._index = None
        self._documents: List[Dict] = []
        self._tokenized_corpus: List[List[str]] = []

    def build_index(self, documents: List[Dict]) -> None:
        self._documents = documents
        self._tokenized_corpus = [self._tokenize(doc["text"]) for doc in documents]
        if HAS_BM25:
            self._index = BM25Okapi(self._tokenized_corpus)
        else:
            self._index = SimpleBM25(self._tokenized_corpus)

    def retrieve(self, query: str, top_k: int = 10, allow_list: Optional[Set[str]] = None) -> List[Dict]:
        if not self._index:
            return []

        tokenized_query = self._tokenize(query)
        scores = self._index.get_scores(tokenized_query)

        scored_docs = []
        for i, score in enumerate(scores):
            doc = self._documents[i]
            if allow_list and doc["chunk_id"] not in allow_list:
                continue
            scored_docs.append({
                "chunk_id": doc["chunk_id"],
                "text": doc["text"],
                "metadata": doc.get("metadata", {}),
                "bm25_score": float(score),
            })

        scored_docs.sort(key=lambda x: x["bm25_score"], reverse=True)
        return scored_docs[:top_k]

    def _tokenize(self, text: str) -> List[str]:
        text = text.lower()
        tokens = re.findall(r'\b[\w\-]+\b', text)
        return tokens
