from __future__ import annotations

import os

import gradio as gr
import pandas as pd

from text2sql_demo.db import init_employee_db, run_select_query
from text2sql_demo.model import generate_sql, validate_sql_for_execution


DB_PATH = os.path.join(os.path.dirname(__file__), "data", "employees.db")


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

    result = generate_sql(question=question, schema_prompt=schema_for_prompt)
    sql = result.sql

    exec_error = validate_sql_for_execution(sql)
    if not execute:
        return db.schema_prompt, sql, None, f"Generated SQL (not executed). Raw: {result.raw}"

    if exec_error:
        return db.schema_prompt, sql, None, f"Not executed: {exec_error}\nRaw: {result.raw}"

    try:
        cols, rows = run_select_query(db.path, sql)
        df = _to_dataframe(cols, rows)
        return db.schema_prompt, sql, df, f"Executed successfully. Rows: {len(rows)}"
    except Exception as e:
        return db.schema_prompt, sql, None, f"Execution error: {type(e).__name__}: {e}\nRaw: {result.raw}"


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
    table = gr.Dataframe(label="Query Result", interactive=False, wrap=True)
    status = gr.Textbox(label="Status", lines=3)

    examples = [
        ["Show all departments", True],
        ["List employees in Engineering", True],
        ["What is the average salary by department?", True],
        ["List employees hired after 2021 with their department name", True],
        ["Show top 3 highest salaries with employee names", True],
    ]
    gr.Examples(examples=examples, inputs=[question, execute])

    run.click(fn=handle, inputs=[question, execute], outputs=[schema, sql_out, table, status])


if __name__ == "__main__":
    demo.launch()

