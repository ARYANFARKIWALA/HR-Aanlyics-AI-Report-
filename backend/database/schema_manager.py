"""Module 1: Schema Discovery & Metadata Management.

Establishes:
1. Automatic Schema Discovery via SQLAlchemy Inspector
2. Structured Metadata JSON output
3. Schema Hashing (SHA-256) for versioning & SCHEMA_CHANGED detection
4. Allowlist Source of Truth for M7 Validation and M8 Execution
5. Credentials/Knowledge Split: Outputs structural metadata only, never secrets/PII
"""

import datetime
import hashlib
from typing import Any

from sqlalchemy import Engine, inspect, text


class DiscoveredSchema:
    """Holds structured discovered schema metadata for a database instance."""

    def __init__(
        self,
        database_id: str,
        dialect: str,
        tables: list[dict[str, Any]],
        schema_hash: str,
        discovered_at: str
    ):
        self.database_id = database_id
        self.dialect = dialect
        self.tables = tables
        self.schema_hash = schema_hash
        self.discovered_at = discovered_at

        # Build fast lookup sets for validation allowlists (M7)
        self.table_allowlist: set[str] = {t["table_name"].lower() for t in tables}
        self.column_allowlist_map: dict[str, set[str]] = {
            t["table_name"].lower(): {c["name"].lower() for c in t["columns"]}
            for t in tables
        }

    def is_table_allowed(self, table_name: str) -> bool:
        return table_name.lower() in self.table_allowlist

    def is_column_allowed(self, table_name: str, column_name: str) -> bool:
        tbl = table_name.lower()
        if tbl not in self.column_allowlist_map:
            return False
        return column_name.lower() in self.column_allowlist_map[tbl]

    def to_dict(self) -> dict[str, Any]:
        return {
            "database_id": self.database_id,
            "dialect": self.dialect,
            "schema_hash": self.schema_hash,
            "discovered_at": self.discovered_at,
            "table_count": len(self.tables),
            "tables": self.tables,
            "table_allowlist": sorted(self.table_allowlist),
        }

    def to_rag_schema_text(self) -> str:
        """Generates RAG-ready structural text (no credentials, pure schema structure)."""
        lines = []
        for t in self.tables:
            col_defs = ", ".join([f"{c['name']} ({c['type']})" for c in t["columns"]])
            fk_defs = ""
            if t.get("foreign_keys"):
                fks = [f"{','.join(fk['constrained_columns'])} -> {fk['referred_table']}({','.join(fk['referred_columns'])})" for fk in t["foreign_keys"]]
                fk_defs = f" | Foreign Keys: {'; '.join(fks)}"
            lines.append(f"TABLE {t['table_name']} ({col_defs}){fk_defs}")
        return "\n".join(lines)


class SchemaManager:
    """Discovers, hashes, and maintains schema allowlists per database_id."""

    @classmethod
    def discover_schema(cls, database_id: str, engine: Engine, dialect: str) -> DiscoveredSchema:
        """Inspects target engine and constructs structured metadata JSON."""
        inspector = inspect(engine)
        table_names = inspector.get_table_names()

        discovered_tables = []
        hash_elements = []

        for table_name in sorted(table_names):
            columns_meta = []
            cols = inspector.get_columns(table_name)
            for c in cols:
                col_name = c["name"]
                col_type = str(c["type"])
                is_pk = bool(c.get("primary_key", False))
                is_nullable = bool(c.get("nullable", True))
                columns_meta.append({
                    "name": col_name,
                    "type": col_type,
                    "primary_key": is_pk,
                    "nullable": is_nullable
                })
                hash_elements.append(f"{table_name}.{col_name}:{col_type}")

            fks = []
            for fk in inspector.get_foreign_keys(table_name):
                fks.append({
                    "constrained_columns": fk.get("constrained_columns", []),
                    "referred_table": fk.get("referred_table", ""),
                    "referred_columns": fk.get("referred_columns", [])
                })

            pk_constraint = inspector.get_pk_constraint(table_name)
            pk_cols = pk_constraint.get("constrained_columns", []) if pk_constraint else []

            # Optional approximate row count
            row_count = 0
            try:
                with engine.connect() as conn:
                    res = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    row_count = res.scalar() or 0
            except Exception:
                row_count = 0

            discovered_tables.append({
                "table_name": table_name,
                "row_count": row_count,
                "columns": columns_meta,
                "primary_keys": pk_cols,
                "foreign_keys": fks
            })

        # Calculate SHA-256 schema hash
        schema_raw_str = "|".join(hash_elements)
        schema_hash = hashlib.sha256(schema_raw_str.encode("utf-8")).hexdigest()
        discovered_at = datetime.datetime.utcnow().isoformat() + "Z"

        return DiscoveredSchema(
            database_id=database_id,
            dialect=dialect,
            tables=discovered_tables,
            schema_hash=schema_hash,
            discovered_at=discovered_at
        )
