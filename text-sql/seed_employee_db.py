#!/usr/bin/env python3
"""
Reset the employee database and seed it with sample data (including Engineering employees).
Use this to get a fresh DB for testing queries like "List employees in Engineering".

Usage:
  python seed_employee_db.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from text2sql_demo.db import init_employee_db

DB_PATH = Path(__file__).resolve().parent / "data" / "employees.db"


def main():
    if DB_PATH.exists():
        os.remove(DB_PATH)
        print(f"Removed existing {DB_PATH}")
    db = init_employee_db(str(DB_PATH))
    print(f"Created and seeded {db.path}")
    # Quick check: count Engineering employees
    import sqlite3
    con = sqlite3.connect(str(DB_PATH))
    n = con.execute(
        "SELECT COUNT(*) FROM employees e JOIN departments d ON e.dept_id = d.dept_id WHERE d.dept_name = 'Engineering'"
    ).fetchone()[0]
    con.close()
    print(f"Engineering employees: {n}. Run the app and try: List employees in Engineering")


if __name__ == "__main__":
    main()
