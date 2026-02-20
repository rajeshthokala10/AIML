#!/usr/bin/env python3
"""
Benchmark text-to-SQL model: exact match and execution match on eval_employee.jsonl.
Usage:
  python run_benchmark.py [--model_id PATH] [--eval_file data/eval_employee.jsonl] [--db_path data/employees.db] [--output results.json]
"""
from __future__ import annotations

# Disable Hugging Face background safetensors conversion thread (avoids JSONDecodeError in thread)
import os
os.environ.setdefault("DISABLE_SAFETENSORS_CONVERSION", "1")

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

# Ensure text2sql_demo is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from text2sql_demo.db import init_employee_db, run_select_query
from text2sql_demo.model import generate_sql, validate_sql_for_execution

SCHEMA_PROMPT = (
    "CREATE TABLE departments (dept_id INTEGER PRIMARY KEY, dept_name TEXT, location TEXT); "
    "CREATE TABLE employees (emp_id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT, title TEXT, hire_date TEXT, dept_id INTEGER, email TEXT, "
    "FOREIGN KEY (dept_id) REFERENCES departments(dept_id)); "
    "CREATE TABLE salaries (emp_id INTEGER, effective_date TEXT, salary INTEGER, "
    "FOREIGN KEY (emp_id) REFERENCES employees(emp_id));"
)


def normalize_sql(s: str) -> str:
    """Lowercase and collapse whitespace for comparison."""
    s = re.sub(r"\s+", " ", s.strip().lower()).strip()
    return s.rstrip(";")


def run_safe(db_path: str, sql: str):
    """Execute SELECT and return (columns, list of rows as dicts) or (None, error_str)."""
    err = validate_sql_for_execution(sql)
    if err:
        return None, err
    try:
        cols, rows = run_select_query(db_path, sql)
        return (cols, rows), None
    except Exception as e:
        return None, str(e)


def rows_match(a: list[dict], b: list[dict]) -> bool:
    """Compare two result sets (order-independent by row content)."""
    if len(a) != len(b):
        return False
    # Normalize: sort keys and represent rows as tuples of values
    def norm(rows):
        return sorted(
            tuple(r[k] for k in sorted(r.keys()))
            for r in rows
        )
    return norm(a) == norm(b)


def load_eval(path: str) -> list[dict]:
    out = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def main():
    parser = argparse.ArgumentParser(description="Benchmark text-to-SQL model")
    parser.add_argument("--model_id", default=None, help="Model path or HuggingFace ID (default: cssupport/t5-small-awesome-text-to-sql)")
    parser.add_argument("--eval_file", default="data/eval_employee.jsonl", help="Path to eval JSONL")
    parser.add_argument("--db_path", default="data/employees.db", help="Path to SQLite DB")
    parser.add_argument("--output", default=None, help="Write results JSON here")
    parser.add_argument("--clear_cache", action="store_true", help="Clear model cache (use when switching model)")
    parser.add_argument("--use_rag", action="store_true", help="Use RAG: retrieve similar (question, SQL) examples as few-shot")
    parser.add_argument("--rag_examples", default="data/train_employee.jsonl", help="JSONL path for RAG examples (question, gold_sql)")
    parser.add_argument("--rag_top_k", type=int, default=3, help="Number of similar examples to use (default 3)")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    eval_path = root / args.eval_file
    db_path = root / args.db_path

    if not eval_path.exists():
        print(f"Eval file not found: {eval_path}", file=sys.stderr)
        sys.exit(1)

    init_employee_db(str(db_path))

    eval_data = load_eval(str(eval_path))
    model_id = args.model_id or "cssupport/t5-small-awesome-text-to-sql"
    rag_path = root / args.rag_examples if args.use_rag else None

    if args.clear_cache:
        from text2sql_demo.model import _load
        _load.cache_clear()

    exact_match = 0
    execution_match = 0
    results = []

    for i, item in enumerate(eval_data):
        question = item["question"]
        gold_sql = item["gold_sql"]
        gen_kw = {"question": question, "schema_prompt": SCHEMA_PROMPT, "model_id": model_id}
        if args.use_rag and rag_path and rag_path.exists():
            gen_kw["use_rag"] = True
            gen_kw["rag_examples_path"] = str(rag_path)
            gen_kw["rag_top_k"] = args.rag_top_k
        pred = generate_sql(**gen_kw)
        pred_sql = pred.sql

        norm_gold = normalize_sql(gold_sql)
        norm_pred = normalize_sql(pred_sql)
        ex = norm_gold == norm_pred
        if ex:
            exact_match += 1

        gold_out, gold_err = run_safe(str(db_path), gold_sql)
        pred_out, pred_err = run_safe(str(db_path), pred_sql)

        if gold_err:
            exec_ok = False
            exec_note = f"gold_error: {gold_err}"
        elif pred_err:
            exec_ok = False
            exec_note = f"pred_error: {pred_err}"
        else:
            (_, gold_rows), (_, pred_rows) = gold_out, pred_out
            exec_ok = rows_match(gold_rows, pred_rows)
            exec_note = "match" if exec_ok else "result_mismatch"
        if exec_ok:
            execution_match += 1

        results.append({
            "question": question,
            "gold_sql": gold_sql,
            "pred_sql": pred_sql,
            "exact_match": ex,
            "execution_match": exec_ok,
            "exec_note": exec_note,
        })

    n = len(eval_data)
    exact_pct = 100.0 * exact_match / n if n else 0
    exec_pct = 100.0 * execution_match / n if n else 0

    summary = {
        "model_id": model_id,
        "eval_file": str(eval_path),
        "n_samples": n,
        "exact_match_count": exact_match,
        "exact_match_pct": round(exact_pct, 2),
        "execution_match_count": execution_match,
        "execution_match_pct": round(exec_pct, 2),
        "results": results,
    }

    print(f"Model: {model_id}")
    print(f"Eval: {eval_path} ({n} samples)")
    print(f"Exact match:     {exact_match}/{n} = {exact_pct:.2f}%")
    print(f"Execution match: {execution_match}/{n} = {exec_pct:.2f}%")

    if args.output:
        out_path = root / args.output
        with open(out_path, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"Results written to {out_path}")

    return summary


if __name__ == "__main__":
    main()
