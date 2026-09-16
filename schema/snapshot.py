"""Module 3: Schema Snapshot & Drift Detection Manager.

Captures canonical structural schema snapshots, generates SHA-256 hashes,
diffs snapshots to detect schema drift (TABLE_ADDED, COLUMN_REMOVED, TYPE_CHANGED),
and persists audit change records.
"""

import hashlib
import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from backend.database.models_schema import SchemaChange, SchemaSnapshot

logger = logging.getLogger("schema.snapshot")


class SchemaSnapshotManager:
    """Manages versioned schema snapshots and drift/change detection."""

    def __init__(self, db: Session):
        self.db = db

    @classmethod
    def compute_schema_hash(cls, snapshot_dict: dict[str, Any]) -> str:
        """Generates a deterministic SHA-256 hash from a canonical snapshot dictionary."""
        canonical_str = json.dumps(snapshot_dict, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    def build_canonical_snapshot(
        self,
        database_id: str,
        tables_data: list[dict[str, Any]],
        relationships_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Builds a deterministic, sorted snapshot representation of the schema structure."""
        sorted_tables = []
        for tbl in sorted(tables_data, key=lambda x: x["table_name"]):
            cols = sorted(tbl.get("columns", []), key=lambda x: x["name"])
            sorted_cols = [
                {
                    "name": c["name"],
                    "data_type": c.get("data_type", ""),
                    "is_primary_key": bool(c.get("is_primary_key", False)),
                    "is_nullable": bool(c.get("is_nullable", True)),
                    "default_value": c.get("default_value")
                }
                for c in cols
            ]
            sorted_tables.append({
                "table_name": tbl["table_name"],
                "table_type": tbl.get("table_type", "TABLE"),
                "primary_keys": sorted(tbl.get("primary_keys", [])),
                "foreign_keys": sorted(
                    tbl.get("foreign_keys", []),
                    key=lambda fk: (fk.get("referred_table", ""), ",".join(fk.get("constrained_columns", [])))
                ),
                "columns": sorted_cols
            })

        sorted_rels = sorted(
            relationships_data,
            key=lambda r: (r.get("source_table", ""), r.get("target_table", ""), r.get("source_column", ""))
        )

        return {
            "database_id": database_id,
            "table_count": len(sorted_tables),
            "tables": sorted_tables,
            "relationships": sorted_rels
        }

    def detect_changes(
        self,
        old_snapshot: dict[str, Any] | None,
        new_snapshot: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Compares two snapshots and generates a granular list of changes."""
        changes: list[dict[str, Any]] = []
        if not old_snapshot:
            # Initial discovery snapshot - everything is freshly discovered
            return changes

        old_tables_map = {t["table_name"]: t for t in old_snapshot.get("tables", [])}
        new_tables_map = {t["table_name"]: t for t in new_snapshot.get("tables", [])}

        old_tbl_names = set(old_tables_map.keys())
        new_tbl_names = set(new_tables_map.keys())

        # 1. Tables Added
        for added_tbl in new_tbl_names - old_tbl_names:
            changes.append({
                "change_type": "TABLE_ADDED",
                "target_name": added_tbl,
                "details": {"table_type": new_tables_map[added_tbl].get("table_type", "TABLE")}
            })

        # 2. Tables Removed
        for removed_tbl in old_tbl_names - new_tbl_names:
            changes.append({
                "change_type": "TABLE_REMOVED",
                "target_name": removed_tbl,
                "details": {"table_type": old_tables_map[removed_tbl].get("table_type", "TABLE")}
            })

        # 3. Tables Modified (Columns & Types)
        for common_tbl in old_tbl_names & new_tbl_names:
            old_tbl = old_tables_map[common_tbl]
            new_tbl = new_tables_map[common_tbl]

            old_cols_map = {c["name"]: c for c in old_tbl.get("columns", [])}
            new_cols_map = {c["name"]: c for c in new_tbl.get("columns", [])}

            old_col_names = set(old_cols_map.keys())
            new_col_names = set(new_cols_map.keys())

            # Columns Added
            for added_col in new_col_names - old_col_names:
                col_info = new_cols_map[added_col]
                changes.append({
                    "change_type": "COLUMN_ADDED",
                    "target_name": f"{common_tbl}.{added_col}",
                    "details": {"data_type": col_info.get("data_type"), "is_nullable": col_info.get("is_nullable")}
                })

            # Columns Removed
            for removed_col in old_col_names - new_col_names:
                col_info = old_cols_map[removed_col]
                changes.append({
                    "change_type": "COLUMN_REMOVED",
                    "target_name": f"{common_tbl}.{removed_col}",
                    "details": {"data_type": col_info.get("data_type")}
                })

            # Columns Type or Nullability Changed
            for col_name in old_col_names & new_col_names:
                oc = old_cols_map[col_name]
                nc = new_cols_map[col_name]

                if oc.get("data_type") != nc.get("data_type"):
                    changes.append({
                        "change_type": "COLUMN_TYPE_CHANGED",
                        "target_name": f"{common_tbl}.{col_name}",
                        "details": {
                            "old_type": oc.get("data_type"),
                            "new_type": nc.get("data_type")
                        }
                    })

                if oc.get("is_nullable") != nc.get("is_nullable"):
                    changes.append({
                        "change_type": "COLUMN_NULLABILITY_CHANGED",
                        "target_name": f"{common_tbl}.{col_name}",
                        "details": {
                            "old_nullable": oc.get("is_nullable"),
                            "new_nullable": nc.get("is_nullable")
                        }
                    })

        return changes

    def create_snapshot(
        self,
        database_id: str,
        canonical_snapshot: dict[str, Any],
        schema_hash: str,
        user_id: int | None = None
    ) -> tuple[SchemaSnapshot, list[dict[str, Any]]]:
        """Saves a new versioned snapshot and logs detected schema drift/changes."""
        # Find latest snapshot for this database
        latest_snapshot = (
            self.db.query(SchemaSnapshot)
            .filter(SchemaSnapshot.database_id == database_id)
            .order_by(SchemaSnapshot.version_number.desc())
            .first()
        )

        old_snapshot_dict = latest_snapshot.snapshot_json if latest_snapshot else None
        changes_detected = self.detect_changes(old_snapshot_dict, canonical_snapshot)

        # Increment version
        new_version = (latest_snapshot.version_number + 1) if latest_snapshot else 1

        snapshot = SchemaSnapshot(
            database_id=database_id,
            version_number=new_version,
            schema_hash=schema_hash,
            table_count=canonical_snapshot.get("table_count", 0),
            column_count=sum(len(t.get("columns", [])) for t in canonical_snapshot.get("tables", [])),
            relationship_count=len(canonical_snapshot.get("relationships", [])),
            snapshot_json=canonical_snapshot,
            created_by_id=user_id
        )
        self.db.add(snapshot)
        self.db.flush()

        # Record SchemaChanges
        for chg in changes_detected:
            self.db.add(SchemaChange(
                database_id=database_id,
                snapshot_id=snapshot.id,
                change_type=chg["change_type"],
                target_name=chg["target_name"],
                details_json=chg.get("details")
            ))

        self.db.flush()
        return snapshot, changes_detected
