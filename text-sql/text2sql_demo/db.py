from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class DbInfo:
    path: str
    schema_prompt: str


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def init_employee_db(db_path: str) -> DbInfo:
    """
    Creates a small sample employee database if it doesn't exist yet.
    Returns a schema string suitable to include in a prompt.
    """
    _ensure_parent_dir(db_path)

    con = sqlite3.connect(db_path)
    try:
        con.execute("PRAGMA foreign_keys = ON;")

        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS departments (
              dept_id INTEGER PRIMARY KEY,
              dept_name TEXT NOT NULL UNIQUE,
              location TEXT
            );

            CREATE TABLE IF NOT EXISTS employees (
              emp_id INTEGER PRIMARY KEY,
              first_name TEXT NOT NULL,
              last_name TEXT NOT NULL,
              title TEXT,
              hire_date TEXT,
              dept_id INTEGER NOT NULL,
              email TEXT UNIQUE,
              FOREIGN KEY (dept_id) REFERENCES departments(dept_id)
            );

            CREATE TABLE IF NOT EXISTS salaries (
              emp_id INTEGER NOT NULL,
              effective_date TEXT NOT NULL,
              salary INTEGER NOT NULL,
              PRIMARY KEY (emp_id, effective_date),
              FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
            );
            """
        )

        # Seed only if empty
        dept_count = con.execute("SELECT COUNT(*) FROM departments").fetchone()[0]
        if dept_count == 0:
            con.executemany(
                "INSERT INTO departments (dept_id, dept_name, location) VALUES (?, ?, ?)",
                [
                    (10, "Engineering", "Hyderabad"),
                    (20, "Sales", "Bengaluru"),
                    (30, "HR", "Pune"),
                    (40, "Finance", "Mumbai"),
                ],
            )

        emp_count = con.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
        if emp_count == 0:
            con.executemany(
                """
                INSERT INTO employees
                  (emp_id, first_name, last_name, title, hire_date, dept_id, email)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (1, "Asha", "Rao", "Data Scientist", "2022-06-15", 10, "asha.rao@corp.com"),
                    (2, "Vikram", "Nair", "Backend Engineer", "2021-02-01", 10, "vikram.nair@corp.com"),
                    (3, "Neha", "Shah", "Sales Executive", "2020-09-20", 20, "neha.shah@corp.com"),
                    (4, "Rohit", "Iyer", "HR Specialist", "2019-03-10", 30, "rohit.iyer@corp.com"),
                    (5, "Meera", "Kulkarni", "Accountant", "2023-01-05", 40, "meera.k@corp.com"),
                    (6, "Arjun", "Patel", "ML Engineer", "2024-07-08", 10, "arjun.patel@corp.com"),
                    (7, "Priya", "Kumar", "Frontend Engineer", "2023-04-12", 10, "priya.kumar@corp.com"),
                    (8, "Suresh", "Reddy", "DevOps Engineer", "2022-11-01", 10, "suresh.reddy@corp.com"),
                    (9, "Anita", "Desai", "QA Engineer", "2024-01-15", 10, "anita.desai@corp.com"),
                ],
            )

        sal_count = con.execute("SELECT COUNT(*) FROM salaries").fetchone()[0]
        if sal_count == 0:
            con.executemany(
                "INSERT INTO salaries (emp_id, effective_date, salary) VALUES (?, ?, ?)",
                [
                    (1, "2024-01-01", 2200000),
                    (2, "2024-01-01", 1800000),
                    (3, "2024-01-01", 1400000),
                    (4, "2024-01-01", 1200000),
                    (5, "2024-01-01", 1300000),
                    (6, "2024-08-01", 2000000),
                    (7, "2024-01-01", 1700000),
                    (8, "2024-01-01", 1900000),
                    (9, "2024-01-01", 1500000),
                ],
            )

        con.commit()
    finally:
        con.close()

    schema_prompt = (
        "Database schema:\n"
        "departments(dept_id, dept_name, location)\n"
        "employees(emp_id, first_name, last_name, title, hire_date, dept_id, email)\n"
        "salaries(emp_id, effective_date, salary)\n"
        "Relationships:\n"
        "- employees.dept_id references departments.dept_id\n"
        "- salaries.emp_id references employees.emp_id\n"
    )
    return DbInfo(path=db_path, schema_prompt=schema_prompt)


def run_select_query(db_path: str, sql: str):
    con = sqlite3.connect(db_path)
    try:
        con.row_factory = sqlite3.Row
        cur = con.execute(sql)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        return cols, [dict(r) for r in rows]
    finally:
        con.close()
