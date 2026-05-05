"""Headless end-to-end smoke test (no Streamlit, no API key)."""
import os, sys, json
from pathlib import Path

# Force the heuristic KG path so we don't need an LLM
import yaml
cfg_path = Path(__file__).parent / "config.yaml"
cfg = yaml.safe_load(cfg_path.read_text())
cfg["knowledge_graph"]["builder"] = "heuristic"
cfg["self_critic"]["enabled"] = False  # stub LLM can't score
cfg["reranker"]["enabled"] = True

import graph_rag_app as app

# Patch load_config to return our overridden config
app.load_config = lambda *a, **kw: cfg

ctx = app.build_context(cfg, Path(cfg["project"]["data_dir"]))
print(f"Indexed {len(ctx['chunks'])} chunks")
print(f"KG: {ctx['kg'].number_of_nodes()} nodes, {ctx['kg'].number_of_edges()} edges")

pipeline = app.build_pipeline(ctx)

state = {"query": "What can cause excessive vibration?", "iteration": 0, "trace": []}
final = pipeline.invoke(state)

print("\n=== TRACE ===")
for entry in final["trace"]:
    print(f" - {entry['step']}")

print("\n=== TOP CAUSES ===")
for i, c in enumerate(final.get("causes", []), start=1):
    print(f"E{i} src={c.get('source')} cause_score={c.get('cause_score'):.3f} path={' -> '.join(c.get('cause_path',[])) or 'n/a'}")
    print(f"     {c.get('text','')[:120]}...")

print("\n=== FINAL ANSWER ===")
print(final.get("final") or final.get("draft", "<empty>"))

print("\nSMOKE TEST OK")
