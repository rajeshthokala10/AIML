#!/usr/bin/env python3
"""
Prepare Telugu-only health instruction data for SLM fine-tuning.
Uses open source: MedMCQA-Indic (Telugu), optional custom JSONL.
Output: data/processed/telugu_health_train.jsonl (instruction + output in Telugu).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def load_medmcqa_indic_telugu(split: str = "train", max_samples: int | None = None) -> list[dict]:
    """Load MedMCQA-Indic Telugu subset from Hugging Face (if available)."""
    try:
        from datasets import load_dataset
    except ImportError:
        print("Install: pip install datasets", file=sys.stderr)
        return []

    # Try common dataset IDs; adjust if HF dataset name differs
    for ds_id in ["ai4bharat/medmcqa-indic", "ekacare/MedMCQA-Indic"]:
        try:
            ds = load_dataset(ds_id, "te", split=split, trust_remote_code=True)
            break
        except Exception:
            continue
    else:
        try:
            ds = load_dataset("ai4bharat/medmcqa-indic", split=split, trust_remote_code=True)
            # Filter by language if column exists
            if "lang" in ds.column_names:
                ds = ds.filter(lambda x: x.get("lang") == "te")
            elif "language" in ds.column_names:
                ds = ds.filter(lambda x: x.get("language") == "te")
        except Exception as e:
            print(f"MedMCQA-Indic not found: {e}. Use --custom_only.", file=sys.stderr)
            return []

    rows = []
    for i, row in enumerate(ds):
        if max_samples and i >= max_samples:
            break
        # Map to instruction/output; field names may vary
        question = row.get("question") or row.get("Question") or row.get("question_te") or ""
        answer = row.get("answer") or row.get("Answer") or row.get("answer_te") or ""
        if not question.strip():
            continue
        rows.append({"instruction": question.strip(), "output": answer.strip() or "N/A"})
    return rows


def load_custom_jsonl(path: str) -> list[dict]:
    """Load custom Telugu health JSONL: lines with 'instruction' and 'output'."""
    out = []
    p = Path(path)
    if not p.exists():
        return out
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if "instruction" in obj and "output" in obj:
                    out.append({"instruction": obj["instruction"], "output": obj["output"]})
            except json.JSONDecodeError:
                continue
    return out


def main():
    parser = argparse.ArgumentParser(description="Prepare Telugu health train data")
    parser.add_argument("--sources", nargs="+", default=["medmcqa_indic"],
                        help="Data sources: medmcqa_indic, custom_faqs")
    parser.add_argument("--medmcqa_max", type=int, default=5000, help="Max samples from MedMCQA-Indic")
    parser.add_argument("--custom_path", default="data/raw/telugu_health_faqs_sample.jsonl",
                        help="Path to custom Telugu FAQ JSONL")
    parser.add_argument("--output", default="data/processed/telugu_health_train.jsonl",
                        help="Output JSONL path")
    args = parser.parse_args()

    out_path = ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)

    all_rows = []
    if "medmcqa_indic" in args.sources:
        rows = load_medmcqa_indic_telugu(split="train", max_samples=args.medmcqa_max)
        all_rows.extend(rows)
        print(f"MedMCQA-Indic (Telugu): {len(rows)} samples")
    if "custom_faqs" in args.sources:
        custom = load_custom_jsonl(str(ROOT / args.custom_path))
        all_rows.extend(custom)
        print(f"Custom FAQs: {len(custom)} samples")

    if not all_rows:
        print("No data. Add custom_faqs at data/raw/telugu_health_faqs.jsonl or fix MedMCQA-Indic.", file=sys.stderr)
        # Write minimal example so pipeline can run
        example = {
            "instruction": "పోషకాహారంలో ప్రోటీన్ ఎందుకు ముఖ్యం?",
            "output": "ప్రోటీన్ కండరాలు, ఎముకలు మరియు చర్మం నిర్మాణానికి అవసరం. ఆహారంలో ప్రోటీన్ తగినంత ఉండాలి."
        }
        all_rows = [example]
        print("Wrote 1 example row. Add real data and re-run.", file=sys.stderr)

    with open(out_path, "w", encoding="utf-8") as f:
        for r in all_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Total: {len(all_rows)} samples -> {out_path}")


if __name__ == "__main__":
    main()
