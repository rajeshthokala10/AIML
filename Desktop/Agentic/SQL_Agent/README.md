# Agentic Text-to-SQL SLM

A 7-day sprint project to build an agentic Text-to-SQL system using Small Language Models (SLMs).

## Day 1 — Foundation + Schema Ingestion

### Project Structure
```
SQL_Agent/
├── data/
│   ├── schema.xlsx       # Excel schema definition (5-6 tables)
│   └── sample.db         # SQLite sample database (100+ rows)
├── ingestion/
│   ├── models.py         # TableSchema dataclass
│   ├── excel_importer.py # Excel → TableSchema list
│   ├── sql_connector.py  # SQLAlchemy → TableSchema list
│   └── normalizer.py     # → canonical CREATE TABLE DDL
├── scripts/
│   ├── create_schema_excel.py  # Generates data/schema.xlsx
│   └── create_sample_db.py     # Generates data/sample.db with 100+ rows
├── requirements.txt
└── test_day1.py          # End-to-end verification
```

### Schema (6 tables, FK chain 4 hops deep)
```
users → orders → order_items → products → categories
users → reviews → products → categories
```

### Setup
```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Generate data files
python scripts/create_schema_excel.py
python scripts/create_sample_db.py

# Run end-to-end test
python test_day1.py
```

### Day 1 Deliverables
- [x] Excel schema importer → `TableSchema` dataclasses
- [x] SQLAlchemy SQL connector → `TableSchema` dataclasses
- [x] Schema normalizer → canonical `CREATE TABLE` DDL with FK annotations
- [x] Both sources produce identical normalized output
- [x] Sample SQLite DB with 6 tables and 100+ rows of realistic data
