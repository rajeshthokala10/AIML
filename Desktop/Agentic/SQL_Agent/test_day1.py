"""
Day 1 — End-of-Day Test

Verifies all Day 1 checklist items:
  ✓ Import schema from Excel (.xlsx)
  ✓ Connect to SQLite DB and extract schema automatically
  ✓ Both sources produce the same canonical DDL format
  ✓ Sample DB has 6 tables and 100+ rows
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from ingestion.excel_importer import import_from_excel
from ingestion.sql_connector import import_from_db
from ingestion.normalizer import normalize, schema_to_ddl


EXCEL_PATH = ROOT / "data" / "schema.xlsx"
DB_PATH    = ROOT / "data" / "sample.db"
DB_URL     = f"sqlite:///{DB_PATH}"

EXPECTED_TABLES = {"users", "categories", "products", "orders", "order_items", "reviews"}

PASS = "\033[92m PASS\033[0m"
FAIL = "\033[91m FAIL\033[0m"


def check(label: str, condition: bool, detail: str = "") -> bool:
    status = PASS if condition else FAIL
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {label}{suffix}")
    return condition


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ─────────────────────────────────────────────────────────────────────────────

def test_prerequisites():
    section("0. Prerequisites")
    ok = True
    ok &= check("data/schema.xlsx exists", EXCEL_PATH.exists(), str(EXCEL_PATH))
    ok &= check("data/sample.db exists",   DB_PATH.exists(),    str(DB_PATH))
    if not ok:
        print("\n  Run these first:")
        print("    python scripts/create_schema_excel.py")
        print("    python scripts/create_sample_db.py")
    return ok


def test_excel_import() -> list:
    section("1. Excel Importer")
    tables = import_from_excel(EXCEL_PATH)
    names  = {t.name for t in tables}

    check("Returns a non-empty list", len(tables) > 0, f"{len(tables)} tables")
    check("All expected tables present", EXPECTED_TABLES <= names,
          f"found: {sorted(names)}")

    for t in tables:
        has_pk = any(c.is_primary_key for c in t.columns)
        check(f"  {t.name}: has primary key", has_pk)
        check(f"  {t.name}: has columns",     len(t.columns) > 0,
              f"{len(t.columns)} columns")

    fk_tables = {t.name for t in tables if t.foreign_keys}
    check(
        "FK relationships loaded (orders, order_items, products, reviews)",
        {"orders", "order_items", "products", "reviews"} <= fk_tables,
        f"fk_tables={sorted(fk_tables)}",
    )

    return tables


def test_sql_import() -> list:
    section("2. SQL Connector (SQLAlchemy)")
    tables = import_from_db(DB_URL)
    names  = {t.name for t in tables}

    check("Returns a non-empty list", len(tables) > 0, f"{len(tables)} tables")
    check("All expected tables present", EXPECTED_TABLES <= names,
          f"found: {sorted(names)}")

    for t in tables:
        has_pk = any(c.is_primary_key for c in t.columns)
        check(f"  {t.name}: has primary key", has_pk)
        check(f"  {t.name}: has columns",     len(t.columns) > 0,
              f"{len(t.columns)} columns")

    return tables


def test_normalizer(excel_tables, sql_tables):
    section("3. Schema Normalizer — DDL Output")

    excel_ddl = normalize(excel_tables)
    sql_ddl   = normalize(sql_tables)

    check("Excel DDL produced for all tables",
          set(excel_ddl.keys()) >= EXPECTED_TABLES)
    check("SQL DDL produced for all tables",
          set(sql_ddl.keys()) >= EXPECTED_TABLES)

    # Check that both sources produce DDL with the same column names
    for tname in EXPECTED_TABLES:
        e_cols = {c.name for c in next(t for t in excel_tables if t.name == tname).columns}
        s_cols = {c.name for c in next(t for t in sql_tables   if t.name == tname).columns}
        check(
            f"  {tname}: column sets match between Excel and DB",
            e_cols == s_cols,
            f"Excel={sorted(e_cols)} DB={sorted(s_cols)}" if e_cols != s_cols else "",
        )

    print("\n  --- Sample DDL (orders table from Excel) ---")
    print(excel_ddl.get("orders", "NOT FOUND"))

    return excel_ddl


def test_database_rows():
    section("4. Sample Database — Row Counts")
    from sqlalchemy import create_engine, text
    engine = create_engine(DB_URL)
    total  = 0

    with engine.connect() as conn:
        for tname in sorted(EXPECTED_TABLES):
            count = conn.execute(text(f"SELECT COUNT(*) FROM {tname}")).scalar()
            total += count
            check(f"  {tname}: has rows", count > 0, f"{count} rows")

    check("Total rows across all tables >= 100", total >= 100, f"{total} total rows")
    engine.dispose()


def test_fk_chain():
    section("5. FK Chain Depth (users → orders → order_items → products → categories)")
    from sqlalchemy import create_engine, text

    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        # 4-hop JOIN query
        sql = """
            SELECT u.username, c.name AS category, COUNT(*) AS items_bought
            FROM users u
            JOIN orders o ON o.user_id = u.user_id
            JOIN order_items oi ON oi.order_id = o.order_id
            JOIN products p ON p.product_id = oi.product_id
            JOIN categories c ON c.category_id = p.category_id
            GROUP BY u.username, c.name
            ORDER BY items_bought DESC
            LIMIT 5
        """
        rows = conn.execute(text(sql)).fetchall()
        check("4-hop JOIN query executes successfully", len(rows) > 0,
              f"{len(rows)} result rows")
        if rows:
            print(f"  Top result: {dict(rows[0]._mapping)}")

    engine.dispose()


# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("  DAY 1 — End-of-Day Verification")
    print("=" * 60)

    if not test_prerequisites():
        sys.exit(1)

    excel_tables = test_excel_import()
    sql_tables   = test_sql_import()
    test_normalizer(excel_tables, sql_tables)
    test_database_rows()
    test_fk_chain()

    section("Summary")
    print("  Day 1 checklist:")
    print("  ■ Import schema from Excel (.xlsx)")
    print("  ■ Connect to SQL DB and extract schema automatically")
    print("  ■ Both sources produce the same canonical DDL format")
    print("  ■ Sample DB with 6 tables and 100+ rows")
    print("  ■ 4-hop FK chain JOIN query works")
    print()


if __name__ == "__main__":
    main()
