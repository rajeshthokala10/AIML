from __future__ import annotations

import json
import os
from pathlib import Path

import gradio as gr
import pandas as pd

from text2sql_demo.db import init_employee_db, run_select_query
from text2sql_demo.model import generate_sql, validate_sql_for_execution

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "employees.db")
# Use fine-tuned model if set: export TEXT2SQL_MODEL_ID=models/t5-text2sql-employee-lora
MODEL_ID = os.environ.get("TEXT2SQL_MODEL_ID")
# RAG: path to (question, gold_sql) examples for few-shot (default: train_employee.jsonl)
RAG_EXAMPLES_PATH = os.environ.get("TEXT2SQL_RAG_EXAMPLES", os.path.join(os.path.dirname(__file__), "data", "train_employee.jsonl"))
FEEDBACK_PATH = os.path.join(os.path.dirname(__file__), "data", "feedback.jsonl")


def save_feedback(question: str, predicted_sql: str, accepted: bool, correct_sql: str = ""):
    """Append one feedback row to data/feedback.jsonl for later re-training."""
    Path(FEEDBACK_PATH).parent.mkdir(parents=True, exist_ok=True)
    row = {
        "question": question,
        "predicted_sql": predicted_sql,
        "accepted": accepted,
        "correct_sql": (correct_sql or "").strip(),
    }
    with open(FEEDBACK_PATH, "a") as f:
        f.write(json.dumps(row) + "\n")
    return "Feedback saved. Use merge_feedback_into_train.py then re-fine-tune to learn from corrections."


def _to_dataframe(cols, rows):
    if not cols:
        return pd.DataFrame([])
    return pd.DataFrame(rows, columns=cols)


def handle(question: str, execute: bool):
    db = init_employee_db(DB_PATH)

    schema_for_prompt = (
        "CREATE TABLE departments (dept_id INTEGER PRIMARY KEY, dept_name TEXT, location TEXT); "
        "CREATE TABLE employees (emp_id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT, title TEXT, hire_date TEXT, dept_id INTEGER, email TEXT, "
        "FOREIGN KEY (dept_id) REFERENCES departments(dept_id)); "
        "CREATE TABLE salaries (emp_id INTEGER, effective_date TEXT, salary INTEGER, "
        "FOREIGN KEY (emp_id) REFERENCES employees(emp_id));"
    )

    gen_kw = {"question": question, "schema_prompt": schema_for_prompt}
    if MODEL_ID:
        gen_kw["model_id"] = MODEL_ID
    # RAG at inference: few-shot from similar (question, SQL) examples
    if Path(RAG_EXAMPLES_PATH).exists():
        gen_kw["use_rag"] = True
        gen_kw["rag_examples_path"] = RAG_EXAMPLES_PATH
        gen_kw["rag_top_k"] = 3
    result = generate_sql(**gen_kw)
    sql = result.sql

    exec_error = validate_sql_for_execution(sql)
    if not execute:
        return db.schema_prompt, sql, None, f"Generated SQL (not executed). Raw: {result.raw}", (question, sql)

    if exec_error:
        return db.schema_prompt, sql, None, f"Not executed: {exec_error}\nRaw: {result.raw}", (question, sql)

    try:
        cols, rows = run_select_query(db.path, sql)
        df = _to_dataframe(cols, rows)
        return db.schema_prompt, sql, df, f"Executed successfully. Rows: {len(rows)}", (question, sql)
    except Exception as e:
        return db.schema_prompt, sql, None, f"Execution error: {type(e).__name__}: {e}\nRaw: {result.raw}", (question, sql)


with gr.Blocks(title="Text to SQL (Employee DB)") as demo:
    gr.Markdown("## Text-to-SQL Converter (Small Model) — Employee Sample DB")
    gr.Markdown(
        "Type a question in English. The model generates a SQLite `SELECT` query for the sample employee database.\n\n"
        "**Safety**: only `SELECT` queries are allowed to run."
    )

    with gr.Row():
        question = gr.Textbox(
            label="Ask a question",
            placeholder="e.g. List employees in Engineering with salary > 1800000",
            lines=2,
        )
    execute = gr.Checkbox(value=True, label="Execute SQL on sample SQLite DB")
    run = gr.Button("Generate (and Execute)")

    schema = gr.Textbox(label="DB Schema (prompt)", lines=8)
    sql_out = gr.Textbox(label="Generated SQL", lines=3)
    table = gr.Dataframe(label="Query Result (review this, then give feedback below)", interactive=False, wrap=True)
    status = gr.Textbox(label="Status", lines=3)

    # Human feedback: state holds (last_question, last_sql) from the last run
    state = gr.State((None, None))

    run.click(
        fn=handle,
        inputs=[question, execute],
        outputs=[schema, sql_out, table, status, state],
    )

    gr.Markdown("---\n### Step 2: Human feedback (after reviewing results above)")
    gr.Markdown(
        "**Flow:** Run the query first → check the **Generated SQL** and **Query Result** above → then say if the answer was correct. "
        "If incorrect, you can provide the correct SQL so the model can be re-trained from your feedback."
    )
    with gr.Row():
        btn_correct = gr.Button("Correct")
        btn_incorrect = gr.Button("Incorrect")
    correct_sql = gr.Textbox(label="Correct SQL (optional, for Incorrect)", placeholder="e.g. SELECT * FROM employees", lines=2)
    feedback_status = gr.Textbox(label="Feedback", interactive=False)

    def on_correct(s):
        if not s or s[0] is None:
            return "Run a query first, then click Correct or Incorrect."
        save_feedback(s[0], s[1], True, "")
        return "Thanks! Marked as correct."

    def on_incorrect(s, correct):
        if not s or s[0] is None:
            return "Run a query first, then click Correct or Incorrect."
        save_feedback(s[0], s[1], False, correct or "")
        return "Thanks! Correction saved. Run: python merge_feedback_into_train.py then re-fine-tune to learn from it."

    btn_correct.click(fn=on_correct, inputs=[state], outputs=[feedback_status])
    btn_incorrect.click(fn=on_incorrect, inputs=[state, correct_sql], outputs=[feedback_status])

    examples = [
        ["Show all departments", True],
        ["List employees in Engineering", True],
        ["What is the average salary by department?", True],
        ["List employees hired after 2021 with their department name", True],
        ["Show top 3 highest salaries with employee names", True],
    ]
    gr.Examples(examples=examples, inputs=[question, execute])


if __name__ == "__main__":
    demo.launch()

