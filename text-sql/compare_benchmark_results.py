#!/usr/bin/env python3
"""
Compare benchmark results: before vs after fine-tuning.
Usage:
  python compare_benchmark_results.py [--before results_baseline.json] [--after results_after_lora.json] [--markdown]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="Compare benchmark results (before vs after fine-tuning)")
    parser.add_argument("--before", default="results_baseline.json", help="Path to baseline results JSON")
    parser.add_argument("--after", default="results_after_lora.json", help="Path to fine-tuned results JSON")
    parser.add_argument("--markdown", action="store_true", help="Print a markdown table and summary")
    args = parser.parse_args()

    before_path = ROOT / args.before
    after_path = ROOT / args.after

    if not before_path.exists():
        print(f"Error: {before_path} not found.")
        return 1
    if not after_path.exists():
        print(f"Error: {after_path} not found.")
        return 1

    before = load(before_path)
    after = load(after_path)

    n = before.get("n_samples", 0)
    exact_before = before.get("exact_match_pct", 0)
    exact_after = after.get("exact_match_pct", 0)
    exec_before = before.get("execution_match_pct", 0)
    exec_after = after.get("execution_match_pct", 0)

    exact_change = exact_after - exact_before
    exec_change = exec_after - exec_before

    if args.markdown:
        print("# Benchmark comparison: before vs after fine-tuning\n")
        print("| Metric | Before (base model) | After (LoRA fine-tuned) | Change |")
        print("|--------|---------------------|-------------------------|--------|")
        print(f"| **Exact match %** | {exact_before:.2f}% | {exact_after:.2f}% | {exact_change:+.2f}% |")
        print(f"| **Execution match %** | {exec_before:.2f}% | {exec_after:.2f}% | {exec_change:+.2f}% |")
        print(f"| **Eval samples** | {n} | {n} | — |")
        print()
        print("**Models:**")
        print(f"- Before: `{before.get('model_id', '—')}`")
        print(f"- After: `{after.get('model_id', '—')}`")
        return 0

    print("Benchmark comparison (before vs after fine-tuning)")
    print("=" * 55)
    print(f"{'Metric':<25} {'Before':>10} {'After':>10} {'Change':>10}")
    print("-" * 55)
    print(f"{'Exact match %':<25} {exact_before:>9.2f}% {exact_after:>9.2f}% {exact_change:>+9.2f}%")
    print(f"{'Execution match %':<25} {exec_before:>9.2f}% {exec_after:>9.2f}% {exec_change:>+9.2f}%")
    print(f"{'Eval samples':<25} {n:>10} {n:>10} {'—':>10}")
    print("=" * 55)
    print(f"Before: {before.get('model_id', '—')}")
    print(f"After:  {after.get('model_id', '—')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
