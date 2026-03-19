from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ColumnSchema:
    name: str
    data_type: str          # SQL type: VARCHAR, INTEGER, DECIMAL, BOOLEAN, TIMESTAMP, TEXT
    is_primary_key: bool = False
    is_nullable: bool = True
    fk_table: Optional[str] = None   # referenced table name if this col is an FK
    fk_column: Optional[str] = None  # referenced column name
    description: str = ""

    def __repr__(self):
        pk = " PK" if self.is_primary_key else ""
        fk = f" FK→{self.fk_table}.{self.fk_column}" if self.fk_table else ""
        null = "" if self.is_nullable else " NOT NULL"
        return f"ColumnSchema({self.name}: {self.data_type}{pk}{fk}{null})"


@dataclass
class ForeignKey:
    from_column: str
    to_table: str
    to_column: str
    cardinality: str = "many-to-one"  # many-to-one | one-to-one

    def __repr__(self):
        return f"FK({self.from_column} → {self.to_table}.{self.to_column})"


@dataclass
class TableSchema:
    name: str
    columns: List[ColumnSchema] = field(default_factory=list)
    foreign_keys: List[ForeignKey] = field(default_factory=list)
    description: str = ""

    @property
    def primary_keys(self) -> List[str]:
        return [c.name for c in self.columns if c.is_primary_key]

    @property
    def column_names(self) -> List[str]:
        return [c.name for c in self.columns]

    def get_column(self, name: str) -> Optional[ColumnSchema]:
        for col in self.columns:
            if col.name == name:
                return col
        return None

    def __repr__(self):
        return (
            f"TableSchema(name={self.name!r}, "
            f"columns={len(self.columns)}, "
            f"fks={len(self.foreign_keys)})"
        )
