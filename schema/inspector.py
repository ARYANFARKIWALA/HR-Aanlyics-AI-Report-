"""Module 3: Deep Schema Inspector.

Discovers tables, views, columns, primary keys, foreign keys, indexes,
and constraints from connected databases via SQLAlchemy Inspector.

STRICT INVARIANT: Under no circumstances does this inspector query or fetch
raw data rows or PII (e.g. no SELECT * FROM employees). Only structural metadata
and aggregate counts are inspected.
"""

import logging
from typing import Any

from sqlalchemy import Engine, inspect, text

logger = logging.getLogger("schema.inspector")


class DeepSchemaInspector:
    """Introspects target database schemas and structures without querying raw row data."""

    def __init__(self, engine: Engine, dialect: str = "sqlite"):
        self.engine = engine
        self.dialect = dialect.lower()

    def inspect_database(self, database_id: str, schema_name: str | None = None) -> dict[str, Any]:
        """Performs deep structural metadata discovery across tables and views.

        Args:
            database_id: Target database identifier
            schema_name: Optional database schema/catalog name

        Returns:
            Structured dictionary containing discovered tables, views, columns,
            PKs, FKs, indexes, and constraints.
        """
        inspector = inspect(self.engine)
        
        # 1. Discover physical tables and views
        try:
            table_names = inspector.get_table_names(schema=schema_name)
        except Exception as e:
            logger.warning(f"Error fetching table names: {e}")
            table_names = []

        try:
            view_names = inspector.get_view_names(schema=schema_name)
        except Exception as e:
            logger.warning(f"Error fetching view names: {e}")
            view_names = []

        discovered_tables: list[dict[str, Any]] = []

        # Process standard tables
        for tbl in table_names:
            tbl_meta = self._inspect_table_or_view(
                inspector=inspector,
                name=tbl,
                table_type="TABLE",
                schema_name=schema_name
            )
            discovered_tables.append(tbl_meta)

        # Process views
        for vw in view_names:
            if vw not in table_names:  # Avoid duplicate if dialect reports view as table
                vw_meta = self._inspect_table_or_view(
                    inspector=inspector,
                    name=vw,
                    table_type="VIEW",
                    schema_name=schema_name
                )
                discovered_tables.append(vw_meta)

        return {
            "database_id": database_id,
            "schema_name": schema_name or "default",
            "dialect": self.dialect,
            "table_count": len(table_names),
            "view_count": len(view_names),
            "total_objects": len(discovered_tables),
            "tables": discovered_tables
        }

    def _inspect_table_or_view(
        self,
        inspector: Any,
        name: str,
        table_type: str,
        schema_name: str | None
    ) -> dict[str, Any]:
        """Inspects an individual table or view."""
        # Columns
        raw_columns = []
        try:
            raw_columns = inspector.get_columns(name, schema=schema_name)
        except Exception as e:
            logger.warning(f"Failed to get columns for {name}: {e}")

        # Primary Key
        pk_cols = []
        try:
            pk_dict = inspector.get_pk_constraint(name, schema=schema_name)
            if pk_dict and "constrained_columns" in pk_dict:
                pk_cols = pk_dict["constrained_columns"]
        except Exception as e:
            logger.warning(f"Failed to get PK constraint for {name}: {e}")

        # Foreign Keys
        foreign_keys = []
        try:
            fks = inspector.get_foreign_keys(name, schema=schema_name)
            for fk in fks:
                foreign_keys.append({
                    "name": fk.get("name") or f"fk_{name}_{fk.get('referred_table', '')}",
                    "constrained_columns": fk.get("constrained_columns", []),
                    "referred_table": fk.get("referred_table", ""),
                    "referred_columns": fk.get("referred_columns", [])
                })
        except Exception as e:
            logger.warning(f"Failed to get FKs for {name}: {e}")

        # Indexes
        indexes = []
        try:
            idx_list = inspector.get_indexes(name, schema=schema_name)
            for idx in idx_list:
                indexes.append({
                    "name": idx.get("name") or f"idx_{name}",
                    "columns": idx.get("column_names", []),
                    "unique": bool(idx.get("unique", False))
                })
        except Exception as e:
            logger.warning(f"Failed to get indexes for {name}: {e}")

        # Constraints (Unique constraints)
        constraints = []
        try:
            unique_constraints = inspector.get_unique_constraints(name, schema=schema_name)
            for uc in unique_constraints:
                constraints.append({
                    "name": uc.get("name") or f"uc_{name}",
                    "type": "UNIQUE",
                    "columns": uc.get("column_names", [])
                })
        except Exception:
            pass

        # Approximate row count (aggregate count only, never fetches rows or data)
        row_count = 0
        if table_type == "TABLE":
            try:
                with self.engine.connect() as conn:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {name}"))
                    row_count = int(result.scalar() or 0)
            except Exception:
                row_count = 0

        # Structured columns
        columns_meta = []
        for idx, col in enumerate(raw_columns, start=1):
            col_name = col.get("name", "")
            raw_type = str(col.get("type", "VARCHAR"))
            is_pk = col_name in pk_cols or bool(col.get("primary_key", False))
            is_nullable = bool(col.get("nullable", True))
            default_val = str(col.get("default")) if col.get("default") is not None else None

            columns_meta.append({
                "ordinal_position": idx,
                "name": col_name,
                "data_type": raw_type,
                "is_primary_key": is_pk,
                "is_nullable": is_nullable,
                "default_value": default_val
            })

        return {
            "table_name": name,
            "table_type": table_type,
            "row_count_approx": row_count,
            "columns": columns_meta,
            "primary_keys": pk_cols,
            "foreign_keys": foreign_keys,
            "indexes": indexes,
            "constraints": constraints
        }
