"""
Smart Chunking Strategies for manufacturing documents.

Provides three strategies:
1. Semantic Chunking — splits on topic boundaries using sentence similarity
2. Recursive Character Chunking — splits hierarchically by separators
3. Sliding Window Chunking — overlapping fixed-size windows

A HybridChunker auto-selects the best strategy per document type.
"""

import re
from dataclasses import dataclass, field
from document_ingestion import Document
import numpy as np


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)
    chunk_id: int = 0
    strategy: str = ""


def _split_sentences(text: str) -> list[str]:
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    return [s.strip() for s in sentences if s.strip()]


class SemanticChunker:
    """
    Splits text at semantic boundaries by measuring cosine similarity between
    consecutive sentence groups. When similarity drops below a threshold,
    a chunk boundary is inserted.
    """

    def __init__(self, model=None, similarity_threshold: float = 0.45,
                 min_chunk_size: int = 100, max_chunk_size: int = 1500):
        self.model = model
        self.similarity_threshold = similarity_threshold
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size

    def chunk(self, doc: Document) -> list[Chunk]:
        sentences = _split_sentences(doc.content)
        if len(sentences) <= 2:
            return [Chunk(text=doc.content, metadata=doc.metadata.copy(),
                         chunk_id=0, strategy="semantic")]

        if self.model is None:
            return self._fallback_chunk(doc, sentences)

        embeddings = self.model.encode(sentences, show_progress_bar=False)
        boundaries = self._find_boundaries(embeddings)
        return self._build_chunks(doc, sentences, boundaries)

    def _find_boundaries(self, embeddings: np.ndarray) -> list[int]:
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = np.dot(embeddings[i], embeddings[i + 1]) / (
                np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[i + 1]) + 1e-8
            )
            similarities.append(sim)

        boundaries = [0]
        for i, sim in enumerate(similarities):
            if sim < self.similarity_threshold:
                boundaries.append(i + 1)
        return boundaries

    def _build_chunks(self, doc: Document, sentences: list[str],
                      boundaries: list[int]) -> list[Chunk]:
        chunks = []
        for i in range(len(boundaries)):
            start = boundaries[i]
            end = boundaries[i + 1] if i + 1 < len(boundaries) else len(sentences)
            text = " ".join(sentences[start:end])

            if len(text) < self.min_chunk_size and chunks:
                chunks[-1].text += " " + text
                continue
            if len(text) > self.max_chunk_size:
                sub_chunks = self._split_large(text, doc, len(chunks))
                chunks.extend(sub_chunks)
                continue

            meta = doc.metadata.copy()
            meta["sentence_range"] = f"{start}-{end-1}"
            chunks.append(Chunk(text=text, metadata=meta,
                               chunk_id=len(chunks), strategy="semantic"))
        return chunks

    def _split_large(self, text: str, doc: Document, start_id: int) -> list[Chunk]:
        words = text.split()
        target_size = self.max_chunk_size
        chunks = []
        current = []
        current_len = 0

        for word in words:
            current.append(word)
            current_len += len(word) + 1
            if current_len >= target_size:
                meta = doc.metadata.copy()
                chunks.append(Chunk(
                    text=" ".join(current), metadata=meta,
                    chunk_id=start_id + len(chunks), strategy="semantic"
                ))
                current = []
                current_len = 0

        if current:
            if chunks and current_len < self.min_chunk_size:
                chunks[-1].text += " " + " ".join(current)
            else:
                meta = doc.metadata.copy()
                chunks.append(Chunk(
                    text=" ".join(current), metadata=meta,
                    chunk_id=start_id + len(chunks), strategy="semantic"
                ))
        return chunks

    def _fallback_chunk(self, doc: Document, sentences: list[str]) -> list[Chunk]:
        chunks = []
        current = []
        current_len = 0
        for sent in sentences:
            if current_len + len(sent) > self.max_chunk_size and current:
                meta = doc.metadata.copy()
                chunks.append(Chunk(
                    text=" ".join(current), metadata=meta,
                    chunk_id=len(chunks), strategy="semantic-fallback"
                ))
                current = []
                current_len = 0
            current.append(sent)
            current_len += len(sent) + 1

        if current:
            meta = doc.metadata.copy()
            chunks.append(Chunk(
                text=" ".join(current), metadata=meta,
                chunk_id=len(chunks), strategy="semantic-fallback"
            ))
        return chunks


class RecursiveChunker:
    """
    Splits text hierarchically using separators in priority order:
    section headers → paragraphs → sentences → words.
    Ideal for structured documents like SOPs and manuals.
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = [
            r'\n===.*?===\n',      # section headers
            r'\n\d+\.\d+\s',      # numbered subsections
            r'\n\n',               # double newline (paragraphs)
            r'\n',                 # single newline
            r'(?<=[.!?])\s+',     # sentence boundaries
            r'\s+',               # word boundaries
        ]

    def chunk(self, doc: Document) -> list[Chunk]:
        pieces = self._recursive_split(doc.content, 0)
        return self._merge_pieces(pieces, doc)

    def _recursive_split(self, text: str, level: int) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text]

        if level >= len(self.separators):
            return [text[:self.chunk_size]]

        pattern = self.separators[level]
        splits = re.split(pattern, text)
        splits = [s for s in splits if s.strip()]

        if len(splits) <= 1:
            return self._recursive_split(text, level + 1)

        result = []
        for split in splits:
            if len(split) <= self.chunk_size:
                result.append(split)
            else:
                result.extend(self._recursive_split(split, level + 1))
        return result

    def _merge_pieces(self, pieces: list[str], doc: Document) -> list[Chunk]:
        chunks = []
        current_text = ""

        for piece in pieces:
            if len(current_text) + len(piece) <= self.chunk_size:
                current_text += ("\n" if current_text else "") + piece
            else:
                if current_text.strip():
                    meta = doc.metadata.copy()
                    chunks.append(Chunk(
                        text=current_text.strip(), metadata=meta,
                        chunk_id=len(chunks), strategy="recursive"
                    ))
                overlap = current_text[-self.chunk_overlap:] if len(current_text) > self.chunk_overlap else ""
                current_text = overlap + "\n" + piece

        if current_text.strip():
            meta = doc.metadata.copy()
            chunks.append(Chunk(
                text=current_text.strip(), metadata=meta,
                chunk_id=len(chunks), strategy="recursive"
            ))
        return chunks


class SlidingWindowChunker:
    """
    Fixed-size sliding window with configurable overlap.
    Best for dense tabular or uniform content like Excel data.
    """

    def __init__(self, window_size: int = 800, step_size: int = 400):
        self.window_size = window_size
        self.step_size = step_size

    def chunk(self, doc: Document) -> list[Chunk]:
        text = doc.content
        if len(text) <= self.window_size:
            return [Chunk(text=text, metadata=doc.metadata.copy(),
                         chunk_id=0, strategy="sliding_window")]

        chunks = []
        start = 0
        while start < len(text):
            end = min(start + self.window_size, len(text))
            window = text[start:end]

            if end < len(text):
                last_period = window.rfind(".")
                last_newline = window.rfind("\n")
                break_at = max(last_period, last_newline)
                if break_at > self.window_size * 0.5:
                    window = text[start:start + break_at + 1]
                    end = start + break_at + 1

            meta = doc.metadata.copy()
            meta["window_start"] = start
            meta["window_end"] = end
            chunks.append(Chunk(
                text=window.strip(), metadata=meta,
                chunk_id=len(chunks), strategy="sliding_window"
            ))

            start += self.step_size
            if end >= len(text):
                break

        return chunks


class HybridChunker:
    """
    Auto-selects the best chunking strategy based on document type and content:
    - PDF text: Semantic chunking (topic-aware splits)
    - TXT/SOP: Recursive chunking (respects section structure)
    - Excel data: Sliding window (handles tabular data)
    """

    def __init__(self, embedding_model=None):
        self.semantic = SemanticChunker(model=embedding_model)
        self.recursive = RecursiveChunker()
        self.sliding = SlidingWindowChunker()

    def chunk(self, doc: Document) -> list[Chunk]:
        if doc.doc_type == "excel":
            chunks = self.sliding.chunk(doc)
        elif doc.doc_type == "txt":
            chunks = self.recursive.chunk(doc)
        elif doc.doc_type == "pdf":
            if doc.metadata.get("has_tables"):
                chunks = self.recursive.chunk(doc)
            else:
                chunks = self.semantic.chunk(doc)
        else:
            chunks = self.recursive.chunk(doc)

        for chunk in chunks:
            chunk.metadata["source"] = doc.source
            chunk.metadata["doc_type"] = doc.doc_type

        return chunks

    def chunk_documents(self, documents: list[Document]) -> list[Chunk]:
        all_chunks = []
        for doc in documents:
            doc_chunks = self.chunk(doc)
            for i, chunk in enumerate(doc_chunks):
                chunk.chunk_id = len(all_chunks) + i
            all_chunks.extend(doc_chunks)

        strategy_counts = {}
        for c in all_chunks:
            strategy_counts[c.strategy] = strategy_counts.get(c.strategy, 0) + 1

        print(f"\nChunking complete: {len(all_chunks)} chunks from {len(documents)} documents")
        print(f"Strategy distribution: {strategy_counts}")
        avg_len = sum(len(c.text) for c in all_chunks) / max(len(all_chunks), 1)
        print(f"Average chunk size: {avg_len:.0f} characters")

        return all_chunks
