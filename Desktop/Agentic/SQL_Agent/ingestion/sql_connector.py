"""
SQL connector: uses SQLAlchemy inspector to reflect a live DB → list[TableSchema]

Supports any SQLAlchemy-compatible database (SQLite, PostgreSQL, MySQL, etc.)
"""

from __future__ import annotations
from typing import List
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from .models import ColumnSchema, ForeignKey, TableSchema


# Map SQLAlchemy reflected type names → canonical SQL types
_SQLA_TYPE_MAP = {
    "INTEGER": "INTEGER",
    "BIGINT": "BIGINT",
    "SMALLINT": "INTEGER",
    "VARCHAR": "VARCHAR(255)",
    "CHAR": "VARCHAR(255)",
    "TEXT": "TEXT",
    "CLOB": "TEXT",
    "BOOLEAN": "BOOLEAN",
    "FLOAT": "DECIMAL(10,2)",
    "REAL": "DECIMAL(10,2)",
    "NUMERIC": "DECIMAL(10,2)",
    "DECIMAL": "DECIMAL(10,2)",
    "DATETIME": "TIMESTAMP",
    "TIMESTAMP": "TIMESTAMP",
    "DATE": "DATE",
    "BLOB": "TEXT",
}


def _normalise_sqla_type(type_obj) -> str:
    """Convert a SQLAlchemy type object to a canonical string."""
    type_name = type(type_obj).__name__.upper()
    # Check exact match first
    if type_name in _SQLA_TYPE_MAP:
        return _SQLA_TYPE_MAP[type_name]
    # Fallback: use string representation
    raw = str(type_obj).upper().split("(")[0].strip()
    return _SQLA_TYPE_MAP.get(raw, str(type_obj).upper())


def _get_table_comment(engine: Engine, table_name: str) -> str:
    """Try to fetch a table comment (supported by PostgreSQL, MySQL)."""
    try:
        insp = inspect(engine)
        comment = insp.get_table_comment(table_name)
        return comment.get("text") or ""
    except Exception:
        return ""


def import_from_db(connection_string: str) -> List[TableSchema]:
    """
    Connect to a database and reflect its schema into TableSchema objects.

    Args:
        connection_string: SQLAlchemy connection URL.
            Examples:
                "sqlite:///data/sample.db"
                "postgresql://user:pass@localhost/mydb"

    Returns:
        List of TableSchema objects for every user table found.
    """
    engine = create_engine(connection_string)

    with engine.connect():  # verify connection
        pass

    insp = inspect(engine)
    table_names = insp.get_table_names()

    tables: dict[str, TableSchema] = {}

    # First pass — build all TableSchema objects
    for table_name in table_names:
        columns_info = insp.get_columns(table_name)
        pk_info = insp.get_pk_constraint(table_name)
        pk_cols = set(pk_info.get("constrained_columns", []))

        columns = []
        for col_info in columns_info:
            col = ColumnSchema(
                name=col_info["name"],
                data_type=_normalise_sqla_type(col_info["type"]),
                is_primary_key=col_info["name"] in pk_cols,
                is_nullable=col_info.get("nullable", True),
                description=col_info.get("comment") or "",
            )
            columns.append(col)

        tables[table_name] = TableSchema(
            name=table_name,
            columns=columns,
            description=_get_table_comment(engine, table_name),
        )

    # Second pass — attach foreign keys (all tables exist now)
    for table_name in table_names:
        fk_info_list = insp.get_foreign_keys(table_name)
        for fk_info in fk_info_list:
            # fk_info keys: constrained_columns, referred_table, referred_columns
            for from_col, to_col in zip(
                fk_info["constrained_columns"],
                fk_info["referred_columns"],
            ):
                fk = ForeignKey(
                    from_column=from_col,
                    to_table=fk_info["referred_table"],
                    to_column=to_col,
                )
                tables[table_name].foreign_keys.append(fk)

                # Also annotate the ColumnSchema
                col = tables[table_name].get_column(from_col)
                if col:
                    col.fk_table = fk_info["referred_table"]
                    col.fk_column = to_col

    engine.dispose()
    return list(tables.values())
