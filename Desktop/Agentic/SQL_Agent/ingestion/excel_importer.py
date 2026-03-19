"""
Excel importer: reads schema.xlsx → list[TableSchema]

Expected Excel format (single sheet named "Schema"):
| table_name | column_name | data_type | is_pk | is_nullable | fk_table | fk_column | description |
"""

import pandas as pd
from pathlib import Path
from typing import Union
from .models import ColumnSchema, ForeignKey, TableSchema


# Normalise data-type strings coming from Excel to canonical SQL types
_TYPE_MAP = {
    "int": "INTEGER",
    "integer": "INTEGER",
    "bigint": "BIGINT",
    "varchar": "VARCHAR(255)",
    "string": "VARCHAR(255)",
    "text": "TEXT",
    "bool": "BOOLEAN",
    "boolean": "BOOLEAN",
    "float": "DECIMAL(10,2)",
    "decimal": "DECIMAL(10,2)",
    "numeric": "DECIMAL(10,2)",
    "datetime": "TIMESTAMP",
    "timestamp": "TIMESTAMP",
    "date": "DATE",
}


def _normalise_type(raw: str) -> str:
    if not raw:
        return "TEXT"
    key = str(raw).strip().lower().split("(")[0]
    return _TYPE_MAP.get(key, str(raw).strip().upper())


def _parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in ("yes", "true", "1", "y")


def import_from_excel(path: Union[str, Path]) -> list[TableSchema]:
    """
    Read an Excel file and return a list of TableSchema objects.

    Args:
        path: Path to the .xlsx file.

    Returns:
        List of TableSchema dataclass instances, one per table found.

    Raises:
        FileNotFoundError: If the Excel file does not exist.
        ValueError: If required columns are missing from the sheet.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Excel schema file not found: {path}")

    df = pd.read_excel(path, sheet_name="Schema", dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]

    required = {"table_name", "column_name", "data_type"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Excel sheet 'Schema' is missing columns: {missing}")

    # Replace NaN with empty string for optional fields
    df = df.fillna("")

    tables: dict[str, TableSchema] = {}

    for _, row in df.iterrows():
        table_name = row["table_name"].strip()
        if not table_name:
            continue

        if table_name not in tables:
            tables[table_name] = TableSchema(
                name=table_name,
                description=row.get("table_description", "").strip(),
            )

        col = ColumnSchema(
            name=row["column_name"].strip(),
            data_type=_normalise_type(row["data_type"]),
            is_primary_key=_parse_bool(row.get("is_pk", False)),
            is_nullable=_parse_bool(row.get("is_nullable", True)),
            fk_table=row.get("fk_table", "").strip() or None,
            fk_column=row.get("fk_column", "").strip() or None,
            description=row.get("description", "").strip(),
        )
        tables[table_name].columns.append(col)

        # Build ForeignKey records
        if col.fk_table:
            fk = ForeignKey(
                from_column=col.name,
                to_table=col.fk_table,
                to_column=col.fk_column or "id",
            )
            tables[table_name].foreign_keys.append(fk)

    result = list(tables.values())
    _validate_relationships(result)
    return result


def _validate_relationships(tables: list[TableSchema]) -> None:
    """Warn if any FK references a table not present in the schema."""
    names = {t.name for t in tables}
    for table in tables:
        for fk in table.foreign_keys:
            if fk.to_table not in names:
                print(
                    f"  [WARNING] {table.name}.{fk.from_column} references "
                    f"unknown table '{fk.to_table}'"
                )
