# Text-to-SQL (Employee DB) + Gradio UI

This is a small demo app that converts natural language into SQL using a small open model and runs it against a sample SQLite employee database.

## Setup

```bash
cd AIML
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Then open the local Gradio URL printed in your terminal.

## Notes

- The bundled database is `data/employees.db` (SQLite).
- For safety, the app only executes `SELECT ...` queries.
