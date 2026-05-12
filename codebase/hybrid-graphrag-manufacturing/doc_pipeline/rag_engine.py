"""
RAG Query Engine — ties together ingestion, chunking, embeddings, query correction,
and the clarifier agent into a unified retrieval-augmented generation pipeline.
"""

import textwrap
from pathlib import Path
from document_ingestion import DocumentIngestion
from chunking import HybridChunker
from embeddings import EmbeddingPipeline, SearchResult
from query_correction import QueryCorrector, CorrectedQuery
from clarifier_agent import ClarifierAgent, ClarifierResult, Intent


class RAGEngine:
    """
    End-to-end RAG pipeline for manufacturing documents.

    Pipeline:
    1. Ingest documents (PDF, TXT, Excel)
    2. Chunk with hybrid strategy (semantic / recursive / sliding window)
    3. Embed chunks → FAISS index
    4. At query time: clarify → correct → search → format context
    """

    def __init__(self, input_dir: str = "input_docs",
                 index_dir: str = "vector_store",
                 model_name: str = "all-MiniLM-L6-v2"):
        self.input_dir = Path(input_dir)
        self.index_dir = Path(index_dir)
        self.ingestion = DocumentIngestion()
        self.embedding_pipeline = EmbeddingPipeline(
            model_name=model_name, index_dir=str(index_dir)
        )
        self.chunker = HybridChunker(
            embedding_model=self.embedding_pipeline.get_model()
        )
        self.query_corrector = QueryCorrector()
        self.clarifier = ClarifierAgent()
        self.is_indexed = False

    def index_documents(self, save: bool = True) -> dict:
        """Ingest, chunk, embed, and index all documents in the input directory."""
        print("=" * 60)
        print("STEP 1: Document Ingestion")
        print("=" * 60)
        documents = self.ingestion.ingest_directory(str(self.input_dir))

        print("\n" + "=" * 60)
        print("STEP 2: Smart Chunking")
        print("=" * 60)
        chunks = self.chunker.chunk_documents(documents)

        print("\n" + "=" * 60)
        print("STEP 3: Embedding & Indexing")
        print("=" * 60)
        self.embedding_pipeline.build_index(chunks)

        if save:
            self.embedding_pipeline.save()

        self.is_indexed = True

        stats = {
            "documents_ingested": len(documents),
            "chunks_created": len(chunks),
            "index_vectors": self.embedding_pipeline.index.ntotal,
            "embedding_dim": self.embedding_pipeline.dimension,
            "sources": list({d.source for d in documents}),
        }
        return stats

    def load_index(self) -> None:
        """Load a previously built index from disk."""
        self.embedding_pipeline.load()
        self.is_indexed = True

    def query(self, user_query: str, top_k: int = 5,
              use_context_window: bool = True,
              show_corrections: bool = True,
              show_clarifier: bool = True) -> dict:
        """
        Process a user query through the full RAG pipeline:
        1. Clarifier Agent: classify intent, extract entities, fill slots
        2. Auto-correct and enhance the query
        3. Retrieve relevant chunks (using enriched query)
        4. Format results with source attribution
        """
        if not self.is_indexed:
            raise RuntimeError("No index loaded. Call index_documents() or load_index() first.")

        clarification = self.clarifier.analyze(user_query)

        correction = self.query_corrector.correct(user_query)

        if correction.corrections_applied:
            base_query = correction.expanded
        else:
            base_query = correction.corrected

        search_query = clarification.enriched_query if clarification.entities else base_query

        if use_context_window:
            results = self.embedding_pipeline.search_with_context(
                search_query, top_k=top_k, context_window=1
            )
        else:
            results = self.embedding_pipeline.search(search_query, top_k=top_k)

        formatted = self._format_results(
            results, correction, clarification, show_corrections, show_clarifier
        )

        return {
            "query": user_query,
            "clarification": clarification,
            "correction": correction,
            "results": results,
            "formatted_output": formatted,
            "num_results": len(results),
            "intent": clarification.intent.value,
            "entities": [(e.entity_type, e.normalized) for e in clarification.entities],
            "is_complete": clarification.is_complete,
        }

    def _format_results(self, results: list[SearchResult],
                        correction: CorrectedQuery,
                        clarification: ClarifierResult,
                        show_corrections: bool,
                        show_clarifier: bool) -> str:
        lines = []
        lines.append("=" * 72)
        lines.append(f"  QUERY: {correction.original}")

        if show_clarifier:
            lines.append(self.clarifier.format_analysis(clarification))

        if show_corrections and correction.corrections_applied:
            lines.append(f"  CORRECTED: {correction.corrected}")
            for fix in correction.corrections_applied:
                lines.append(f"    * {fix}")

        lines.append("=" * 72)

        if clarification.clarification_prompt and not clarification.is_complete:
            lines.append("")
            lines.append("  >> CLARIFICATION NEEDED:")
            for line in clarification.clarification_prompt.split("\n"):
                lines.append(f"     {line}")
            lines.append("")

        if not results:
            lines.append("\n  No relevant results found.\n")
            return "\n".join(lines)

        for i, result in enumerate(results, 1):
            source_name = Path(result.metadata.get("source", "unknown")).name
            doc_type = result.metadata.get("doc_type", "unknown")
            score = result.score

            lines.append(f"\n-- Result {i} -- [{doc_type.upper()}] {source_name} "
                         f"(relevance: {score:.3f})")

            extra = []
            if "page" in result.metadata:
                extra.append(f"page {result.metadata['page']}")
            if "sheet_name" in result.metadata:
                extra.append(f"sheet: {result.metadata['sheet_name']}")
            if "section_title" in result.metadata:
                extra.append(f"section: {result.metadata['section_title']}")
            if extra:
                lines.append(f"   Location: {', '.join(extra)}")

            preview = result.text[:600]
            if len(result.text) > 600:
                last_sentence = preview.rfind(".")
                if last_sentence > 400:
                    preview = preview[:last_sentence + 1]
                preview += " [...]"

            wrapped = textwrap.fill(preview, width=72, initial_indent="   ",
                                    subsequent_indent="   ")
            lines.append(wrapped)

        lines.append("\n" + "=" * 72)
        summary_parts = [
            f"{len(results)} results",
            f"intent: {clarification.intent.value}",
            f"entities: {len(clarification.entities)}",
            f"confidence: {correction.confidence:.0%}",
        ]
        lines.append(f"  {' | '.join(summary_parts)}")
        lines.append("=" * 72)

        return "\n".join(lines)

    def interactive_session(self) -> None:
        """Run an interactive query loop in the terminal."""
        print("\n" + "=" * 70)
        print("  MANUFACTURING DOCUMENT QUERY SYSTEM")
        print("  Type your question (or 'quit' to exit)")
        print("=" * 70)

        while True:
            try:
                user_input = input("\n> Query: ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not user_input or user_input.lower() in ("quit", "exit", "q"):
                print("Session ended.")
                break

            result = self.query(user_input)
            print(result["formatted_output"])
