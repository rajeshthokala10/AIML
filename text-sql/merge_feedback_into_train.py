#!/usr/bin/env python3
"""
Merge human feedback (data/feedback.jsonl) into training data for re-fine-tuning.
Entries with correct_sql are turned into (question, gold_sql) and appended to the
output file. Run this, then run finetune_lora.py with the merged file to learn from
corrections.

Usage:
  python merge_feedback_into_train.py [--feedback data/feedback.jsonl] [--train data/train_employee.jsonl] [--output data/train_with_feedback.jsonl]
  python finetune_lora.py --train_file data/train_with_feedback.jsonl --output_dir models/t5-text2sql-employee-lora
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_jsonl(path: str) -> list[dict]:
    out = []
    p = Path(path)
    if not p.exists():
        return out
    with open(p, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def main():
    parser = argparse.ArgumentParser(description="Merge feedback corrections into training data")
    parser.add_argument("--feedback", default="data/feedback.jsonl", help="Path to feedback JSONL")
    parser.add_argument("--train", default="data/train_employee.jsonl", help="Path to existing train JSONL")
    parser.add_argument("--output", default="data/train_with_feedback.jsonl", help="Output merged JSONL for fine-tuning")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    feedback_path = root / args.feedback
    train_path = root / args.train
    output_path = root / args.output

    train_rows = load_jsonl(str(train_path))
    feedback_rows = load_jsonl(str(feedback_path))

    # Only use feedback entries that have a correction (correct_sql) or were accepted (accepted=True -> use predicted_sql as gold)
    new_rows = []
    for row in feedback_rows:
        question = row.get("question", "").strip()
        if not question:
            continue
        correct_sql = (row.get("correct_sql") or "").strip()
        predicted_sql = (row.get("predicted_sql") or "").strip()
        accepted = row.get("accepted", False)
        if correct_sql:
            new_rows.append({"question": question, "gold_sql": correct_sql})
        elif accepted and predicted_sql:
            new_rows.append({"question": question, "gold_sql": predicted_sql})

    if not new_rows:
        print("No feedback corrections to merge. Add entries with 'correct_sql' (or accepted with predicted_sql) in feedback.jsonl.")
        if train_rows:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                for r in train_rows:
                    f.write(json.dumps(r) + "\n")
            print(f"Wrote existing train only to {output_path}")
        return

    # Deduplicate by (question, gold_sql) and avoid duplicates already in train
    train_set = {(r["question"], r["gold_sql"]) for r in train_rows}
    added = 0
    for r in new_rows:
        key = (r["question"], r["gold_sql"])
        if key not in train_set:
            train_set.add(key)
            train_rows.append(r)
            added += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        for r in train_rows:
            f.write(json.dumps(r) + "\n")

    print(f"Merged {added} feedback corrections into {len(train_rows)} total examples.")
    print(f"Output: {output_path}")
    print("Re-fine-tune with: python finetune_lora.py --train_file data/train_with_feedback.jsonl --output_dir models/t5-text2sql-employee-lora")


if __name__ == "__main__":
    main()
