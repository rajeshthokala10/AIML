"""
Streamlit Web UI for the Manufacturing Document RAG Pipeline.
Run: streamlit run app.py
"""

import sys
import os
from pathlib import Path

os.chdir(Path(__file__).parent)

import streamlit as st
import time

st.set_page_config(
    page_title="Manufacturing RAG Pipeline",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header { font-size: 2rem; font-weight: 700; color: #1a237e; margin-bottom: 0; }
    .sub-header { font-size: 1rem; color: #5c6bc0; margin-top: 0; }
    .result-card {
        background: #f5f5f5; border-left: 4px solid #283593;
        padding: 12px 16px; margin: 8px 0; border-radius: 4px;
    }
    .entity-tag {
        display: inline-block; background: #e8eaf6; color: #283593;
        padding: 2px 10px; border-radius: 12px; margin: 2px 4px; font-size: 0.85rem;
    }
    .intent-tag {
        display: inline-block; background: #283593; color: white;
        padding: 4px 14px; border-radius: 16px; font-size: 0.9rem; font-weight: 600;
    }
    .slot-filled { color: #2e7d32; }
    .slot-missing { color: #c62828; }
    .metric-box {
        background: #e8eaf6; border-radius: 8px; padding: 16px; text-align: center;
    }
    .metric-num { font-size: 1.8rem; font-weight: 700; color: #283593; }
    .metric-label { font-size: 0.85rem; color: #5c6bc0; }
    .correction-box {
        background: #fff3e0; border-left: 4px solid #ff9800;
        padding: 10px 14px; border-radius: 4px; margin: 8px 0;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource(show_spinner="Loading RAG engine and building index...")
def load_engine():
    from create_sample_docs import (
        create_quality_control_pdf, create_production_planning_pdf,
        create_safety_compliance_pdf, create_maintenance_pdf,
        create_sop_txt, create_supply_chain_txt, create_production_metrics_excel,
    )
    input_dir = Path("input_docs")
    if not list(input_dir.glob("*.pdf")):
        create_quality_control_pdf()
        create_production_planning_pdf()
        create_safety_compliance_pdf()
        create_maintenance_pdf()
        create_sop_txt()
        create_supply_chain_txt()
        create_production_metrics_excel()

    from rag_engine import RAGEngine
    engine = RAGEngine(input_dir="input_docs", index_dir="vector_store", model_name="all-MiniLM-L6-v2")

    index_path = Path("vector_store/manufacturing_index.faiss")
    if index_path.exists():
        engine.load_index()
    else:
        engine.index_documents(save=True)

    return engine


engine = load_engine()


# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    top_k = st.slider("Results to retrieve", 1, 10, 5)
    use_context = st.checkbox("Context window (neighboring chunks)", value=True)
    show_clarifier = st.checkbox("Show Clarifier Agent analysis", value=True)
    show_corrections = st.checkbox("Show query corrections", value=True)

    st.markdown("---")
    st.markdown("### 📄 Indexed Documents")
    for f in sorted(Path("input_docs").iterdir()):
        icon = {"pdf": "📕", "txt": "📝", "xlsx": "📊"}.get(f.suffix.lstrip("."), "📄")
        st.markdown(f"{icon} `{f.name}`")

    st.markdown("---")
    st.markdown("### 📊 Index Stats")
    col1, col2 = st.columns(2)
    col1.metric("Chunks", engine.embedding_pipeline.index.ntotal)
    col2.metric("Dim", engine.embedding_pipeline.dimension)

    st.markdown("---")
    st.markdown("### 💡 Try these queries")
    examples = [
        "What is the OEE target for Q2 2026?",
        "Why did CNC Line 4 shut down?",
        "Compare Nippon Steel vs ArcelorMittal",
        "safty training requirements for operators",
        "What is the CAPA process for critical NCR?",
        "environmental compliace VOC emissions",
        "How does the kanban system work?",
        "maintanance schedul for spindle bearings",
        "scrap rate for welding Plant A vs Plant B",
        "What is CPK for part TH-4401?",
    ]
    for ex in examples:
        if st.button(ex, key=f"ex_{ex}", use_container_width=True):
            st.session_state["query_input"] = ex


# ── Main Area ───────────────────────────────────────────────────────────────
st.markdown('<p class="main-header">🏭 Manufacturing Document Query System</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">RAG Pipeline — PDF / TXT / Excel ingestion, smart chunking, embeddings, query correction & clarifier agent</p>', unsafe_allow_html=True)
st.markdown("")

query = st.text_input(
    "Ask a question about manufacturing operations:",
    value=st.session_state.get("query_input", ""),
    placeholder="e.g. What is the OEE for Plant A in Q1 2026?",
    key="query_box",
)

if query:
    start = time.time()
    result = engine.query(
        query, top_k=top_k,
        use_context_window=use_context,
        show_corrections=show_corrections,
        show_clarifier=show_clarifier,
    )
    elapsed = time.time() - start

    clarification = result["clarification"]
    correction = result["correction"]

    # ── Metrics row ─────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f'<div class="metric-box"><div class="metric-num">{result["num_results"]}</div>'
                    f'<div class="metric-label">Results</div></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="metric-box"><div class="metric-num">{clarification.intent.value.upper()}</div>'
                    f'<div class="metric-label">Intent ({clarification.intent_confidence:.0%})</div></div>',
                    unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div class="metric-box"><div class="metric-num">{len(clarification.entities)}</div>'
                    f'<div class="metric-label">Entities</div></div>', unsafe_allow_html=True)
    with m4:
        st.markdown(f'<div class="metric-box"><div class="metric-num">{elapsed:.2f}s</div>'
                    f'<div class="metric-label">Latency</div></div>', unsafe_allow_html=True)

    st.markdown("")

    # ── Clarifier + Corrections ─────────────────────────────────────────
    if show_clarifier or show_corrections:
        with st.expander("🔍 Query Analysis", expanded=True):
            c1, c2 = st.columns(2)

            if show_clarifier:
                with c1:
                    st.markdown("**Clarifier Agent**")
                    st.markdown(f'<span class="intent-tag">{clarification.intent.value.upper()}</span> '
                                f'confidence: {clarification.intent_confidence:.0%}',
                                unsafe_allow_html=True)

                    if clarification.entities:
                        st.markdown("**Entities extracted:**")
                        tags = "".join(
                            f'<span class="entity-tag">{e.entity_type}: {e.normalized}</span>'
                            for e in clarification.entities
                        )
                        st.markdown(tags, unsafe_allow_html=True)

                    st.markdown("**Slots:**")
                    for s in clarification.slots:
                        if s.filled:
                            st.markdown(f'<span class="slot-filled">✅ {s.name}</span> = {s.value}',
                                        unsafe_allow_html=True)
                        else:
                            req = "required" if s.required else "optional"
                            st.markdown(f'<span class="slot-missing">❌ {s.name} ({req})</span>',
                                        unsafe_allow_html=True)

                    if not clarification.is_complete:
                        st.warning(clarification.clarification_prompt)

            if show_corrections:
                with c2:
                    st.markdown("**Query Correction**")
                    if correction.corrections_applied:
                        st.markdown(f'<div class="correction-box">'
                                    f'<b>Original:</b> {correction.original}<br>'
                                    f'<b>Corrected:</b> {correction.corrected}</div>',
                                    unsafe_allow_html=True)
                        for fix in correction.corrections_applied:
                            st.markdown(f"  • {fix}")
                    else:
                        st.markdown("✅ No corrections needed")

    # ── Results ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(f"### 📋 Retrieved Results ({result['num_results']})")

    for i, res in enumerate(result["results"], 1):
        source_name = Path(res.metadata.get("source", "unknown")).name
        doc_type = res.metadata.get("doc_type", "unknown").upper()
        score = res.score

        location_parts = []
        if "page" in res.metadata:
            location_parts.append(f"Page {res.metadata['page']}")
        if "sheet_name" in res.metadata:
            location_parts.append(f"Sheet: {res.metadata['sheet_name']}")
        if "section_title" in res.metadata:
            location_parts.append(f"Section: {res.metadata['section_title']}")
        location = " · ".join(location_parts)

        type_colors = {"PDF": "#c62828", "TXT": "#2e7d32", "EXCEL": "#1565c0"}
        type_color = type_colors.get(doc_type, "#555")

        with st.container():
            header_col, score_col = st.columns([5, 1])
            with header_col:
                st.markdown(
                    f'**Result {i}** · '
                    f'<span style="background:{type_color};color:white;padding:2px 8px;border-radius:4px;font-size:0.8rem">{doc_type}</span> '
                    f'`{source_name}`'
                    f'{" · " + location if location else ""}',
                    unsafe_allow_html=True,
                )
            with score_col:
                pct = min(score * 100, 100)
                bar_color = "#2e7d32" if pct > 50 else "#ff9800" if pct > 30 else "#c62828"
                st.markdown(
                    f'<div style="text-align:right">'
                    f'<span style="font-weight:700;color:{bar_color}">{score:.3f}</span></div>',
                    unsafe_allow_html=True,
                )

            preview = res.text[:800]
            if len(res.text) > 800:
                last_dot = preview.rfind(".")
                if last_dot > 500:
                    preview = preview[:last_dot + 1]
                preview += " ..."

            st.markdown(f'<div class="result-card">{preview}</div>', unsafe_allow_html=True)

    # ── Clear button ────────────────────────────────────────────────────
    if st.button("Clear"):
        st.session_state["query_input"] = ""
        st.rerun()
