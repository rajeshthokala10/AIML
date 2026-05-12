"""
Main runner — generates sample documents, indexes them, and runs demo queries
showing the full pipeline:
  ingestion → chunking → embedding → clarifier (intent/entity/slot) → query correction → retrieval
"""

import sys
import os
import time
from pathlib import Path

os.chdir(Path(__file__).parent)

from create_sample_docs import (
    create_quality_control_pdf,
    create_production_planning_pdf,
    create_safety_compliance_pdf,
    create_maintenance_pdf,
    create_sop_txt,
    create_supply_chain_txt,
    create_production_metrics_excel,
)
from rag_engine import RAGEngine
from query_correction import QueryCorrector
from clarifier_agent import ClarifierAgent


def generate_documents():
    print("\n" + "=" * 72)
    print("  GENERATING SAMPLE MANUFACTURING DOCUMENTS")
    print("=" * 72 + "\n")
    create_quality_control_pdf()
    create_production_planning_pdf()
    create_safety_compliance_pdf()
    create_maintenance_pdf()
    create_sop_txt()
    create_supply_chain_txt()
    create_production_metrics_excel()
    print("\n  All 7 documents generated.\n")


def demo_query_correction():
    print("\n" + "=" * 72)
    print("  QUERY AUTO-CORRECTION DEMO")
    print("=" * 72)

    corrector = QueryCorrector()
    test_queries = [
        "what is the maintanance schedul for CNC machines?",
        "show me the OEE and MTBF for plant A equiment",
        "safty compliace report for OSHA inpsection",
        "supplier scorcard for steel procudre",
        "what is the scrap rate for titanim parts in the stamping line?",
        "how do we handle deffect in qualitiy control?",
        "tell me about vibation analysis on spinle bearings",
        "what is the CAPA process for NCR",
        "inventry management and kanban system for spare parts",
        "hydralic pressure specificaiton for CNC machning center",
    ]

    for q in test_queries:
        result = corrector.correct(q)
        print(f"\n  Original:  {result.original}")
        print(f"  Corrected: {result.corrected}")
        if result.corrections_applied:
            for fix in result.corrections_applied:
                print(f"    * {fix}")
        print(f"  Expanded:  {result.expanded[:120]}...")


def demo_clarifier_agent():
    print("\n\n" + "=" * 72)
    print("  CLARIFIER AGENT DEMO — Intent / Entity / Slot Analysis")
    print("=" * 72)

    agent = ClarifierAgent()

    test_queries = [
        # Metric query — fully specified
        "What is the OEE for CNC Machining in Plant A for Q1 2026?",
        # Metric query — missing metric
        "What are the numbers for Plant B?",
        # Troubleshooting — fully specified
        "Why did CNC Line 4 shut down in February?",
        # Troubleshooting — missing equipment
        "Something keeps breaking down, how do I fix it?",
        # Comparison — multi-entity
        "Compare Nippon Steel vs ArcelorMittal on quality and delivery scores",
        # Compliance — with standard
        "Are we compliant with OSHA 29 CFR 1910.147 lockout tagout requirements?",
        # Procedure — well specified
        "How do I perform a tool change on the Mori Seiki NHX5000?",
        # Trend — with time range
        "How has MTBF improved from Q4 2025 to Q1 2026?",
        # Root cause
        "What was the root cause of the spindle bearing failure on CNC-A-004?",
        # Status query
        "What is the current status of the heat treatment furnace HT-B-001?",
        # Vague query — incomplete
        "Tell me about steel",
        # Entity-rich query
        "What is the CPK and scrap rate for part TH-4401 on STAMP-A-002 in March?",
    ]

    for q in test_queries:
        result = agent.analyze(q)
        print("\n" + agent.format_analysis(result))


def demo_queries(engine: RAGEngine):
    print("\n\n" + "=" * 72)
    print("  FULL PIPELINE DEMO — Clarifier + Correction + Retrieval")
    print("=" * 72)

    queries = [
        "What is the OEE target for Q2 2026?",
        "How do we handle non-conformance reports?",
        "What is the maintanance schedul for CNC spindle bearings?",
        "Tell me about supplier scorcard for steel vendors",
        "What are the safty training requirements for new operators?",
        "What happened with CNC Line 4 shutdown in February?",
        "What is the CAPA process timeline for critical defects?",
        "environmental compliace VOC emissions status",
        "Compare the scrap rate between Plant A and Plant B welding",
        "How does the kanban system work for spare parts inventry?",
    ]

    for q in queries:
        result = engine.query(q, top_k=3, show_corrections=True, show_clarifier=True)
        print(result["formatted_output"])
        print()


def main():
    start_time = time.time()

    print("\n" + "#" * 72)
    print("#" + " " * 70 + "#")
    print("#   MANUFACTURING DOCUMENT PROCESSING & RAG PIPELINE" + " " * 19 + "#")
    print("#   with Clarifier Agent (Intent / Entity / Slot Filling)" + " " * 13 + "#")
    print("#" + " " * 70 + "#")
    print("#" * 72)

    # Step 1: Generate sample documents
    generate_documents()

    # Step 2: Show query correction capabilities
    demo_query_correction()

    # Step 3: Show clarifier agent capabilities (standalone)
    demo_clarifier_agent()

    # Step 4: Build the RAG engine and index all documents
    print("\n\n" + "#" * 72)
    print("  BUILDING RAG INDEX")
    print("#" * 72 + "\n")

    engine = RAGEngine(
        input_dir="input_docs",
        index_dir="vector_store",
        model_name="all-MiniLM-L6-v2",
    )
    stats = engine.index_documents(save=True)

    print("\n-- Index Statistics --")
    print(f"  Documents ingested:  {stats['documents_ingested']}")
    print(f"  Chunks created:      {stats['chunks_created']}")
    print(f"  FAISS vectors:       {stats['index_vectors']}")
    print(f"  Embedding dimension: {stats['embedding_dim']}")
    print(f"  Sources:")
    for src in stats['sources']:
        print(f"    * {Path(src).name}")

    # Step 5: Run full pipeline demo queries (clarifier + correction + retrieval)
    demo_queries(engine)

    elapsed = time.time() - start_time
    print(f"\n  Total pipeline time: {elapsed:.1f}s")
    print("  Pipeline complete.\n")


if __name__ == "__main__":
    main()
