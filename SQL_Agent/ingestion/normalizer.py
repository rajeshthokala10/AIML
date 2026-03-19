"""
Normalizer: converts TableSchema objects → canonical CREATE TABLE DDL strings.

Both the Excel importer and SQL connector feed into this module, ensuring a
single, consistent DDL representation regardless of source.
"""

from __future__ import annotations
from typing import Dict, List
from .models import TableSchema


def table_to_ddl(table: "TableSchema") -> str:
    """
    Convert a TableSchema into a canonical CREATE TABLE DDL string.

    The output format is:
        -- <description>
        CREATE TABLE <name> (
            <column> <type> [PRIMARY KEY] [NOT NULL],
            ...
            -- FK: <col> REFERENCES <table>(<col>)
        );

    Args:
        table: A TableSchema dataclass instance.

    Returns:
        A formatted DDL string.
    """
    lines = []

    if table.description:
        lines.append(f"-- {table.description}")

    lines.append(f"CREATE TABLE {table.name} (")

    col_defs = []
    fk_comments = []

    for col in table.columns:
        parts = [f"    {col.name}", col.data_type]

        if col.is_primary_key:
            parts.append("PRIMARY KEY")
        if not col.is_nullable and not col.is_primary_key:
            parts.append("NOT NULL")

        col_line = " ".join(parts)
        if col.description:
            col_line += f"  -- {col.description}"

        col_defs.append(col_line)

        if col.fk_table:
            fk_comments.append(
                f"    -- FK: {col.name} REFERENCES {col.fk_table}({col.fk_column})"
            )

    # Join column definitions with commas
    for i, col_def in enumerate(col_defs):
        sep = "," if i < len(col_defs) - 1 or fk_comments else ""
        lines.append(col_def + sep)

    # Append FK annotation comments at the end
    for i, fk_comment in enumerate(fk_comments):
        lines.append(fk_comment)

    lines.append(");")
    return "\n".join(lines)


def schema_to_ddl(tables: List[TableSchema]) -> str:
    """
    Convert a list of TableSchema objects into a full DDL script.

    Args:
        tables: List of TableSchema objects.

    Returns:
        Multi-table DDL string with tables separated by blank lines.
    """
    ddl_blocks = [table_to_ddl(t) for t in tables]
    return "\n\n".join(ddl_blocks)


def normalize(tables: List[TableSchema]) -> Dict[str, str]:
    """
    Return a mapping of table_name → DDL string for each table.

    Args:
        tables: List of TableSchema objects.

    Returns:
        Dict mapping table name to its DDL.
    """
    return {t.name: table_to_ddl(t) for t in tables}
