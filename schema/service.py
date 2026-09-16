"""Module 3: Schema Intelligence Service.

Orchestrates deep schema discovery, semantic HR metadata classification,
Module 2 SQL repository usage analysis, human metadata governance,
drift/snapshot management, and health scoring.
"""

import datetime
import logging
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func

from backend.database.connection_manager import connection_manager
from backend.database.models_schema import (
    SchemaTable, SchemaColumn, SchemaRelationship, SchemaIndex,
    SchemaConstraint, SchemaSnapshot, SchemaChange, SchemaUsageMetric
)
from .inspector import DeepSchemaInspector
from .hr_mapping import HRMetadataMapper
from .usage_analyzer import SchemaUsageAnalyzer
from .snapshot import SchemaSnapshotManager

logger = logging.getLogger("schema.service")


class SchemaIntelligenceService:
    """Core service for managing HR database schema intelligence and metadata."""

    def __init__(self, db: Session):
        self.db = db

    def discover_schema(self, database_id: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Discovers or refreshes database schema with deep HR intelligence and human edit preservation.

        Flow:
        1. Acquire engine via ConnectionManager (isolated credentials, dialect awareness).
        2. Introspect structures using DeepSchemaInspector (zero raw rows fetched).
        3. Apply HR semantic classification (entities, metrics, dimensions, date roles, sensitivity).
        4. Mine Module 2 SQL repository queries for table/column frequencies and recurring joins.
        5. Calculate table importance scores (0-100).
        6. Preserve existing human-authored business names, definitions, and verification statuses.
        7. Persist updated schema objects and relationships in metadata DB.
        8. Capture snapshot, compute SHA-256 hash, and detect schema changes.
        """
        # 1. Acquire Engine & Dialect
        engine = connection_manager.get_engine(database_id)
        dialect_rules = connection_manager.get_dialect_rules(database_id)
        dialect = dialect_rules.dialect_name if dialect_rules else "sqlite"


        # 2. Inspect Target Database
        inspector = DeepSchemaInspector(engine=engine, dialect=dialect)
        raw_discovery = inspector.inspect_database(database_id)

        # 3. Analyze Module 2 SQL Repository Usage
        usage_analyzer = SchemaUsageAnalyzer(self.db)
        usage_data = usage_analyzer.analyze_repository_usage(database_id)
        table_usage = usage_data.get("table_usage", {})
        inferred_joins = usage_data.get("inferred_joins", [])

        # Fetch existing tables and columns to preserve human edits
        existing_tables = {
            t.table_name: t
            for t in self.db.query(SchemaTable).filter_by(database_id=database_id).all()
        }

        discovered_tables_models: List[SchemaTable] = []
        relationships_to_create: List[Dict[str, Any]] = []

        # 4 & 5 & 6: Process and persist tables and columns
        for tbl in raw_discovery.get("tables", []):
            tbl_name = tbl["table_name"]
            tbl_type = tbl.get("table_type", "TABLE")
            row_count = tbl.get("row_count_approx", 0)
            col_list = tbl.get("columns", [])
            fks = tbl.get("foreign_keys", [])
            pks = tbl.get("primary_keys", [])

            # Check for existing table to preserve human modifications
            existing_tbl = existing_tables.get(tbl_name)

            # Classify HR entity type & effective dating
            entity_type = HRMetadataMapper.classify_table_entity(tbl_name)
            has_effective_dating = HRMetadataMapper.detect_effective_dating([c["name"] for c in col_list])

            # Calculate importance score
            usage_cnt = table_usage.get(tbl_name.lower(), 0)
            importance_score, importance_level = SchemaUsageAnalyzer.calculate_table_importance(
                table_name=tbl_name,
                entity_type=entity_type,
                column_count=len(col_list),
                fk_count=len(fks),
                query_usage_count=usage_cnt
            )

            if existing_tbl:
                # Update structural aspects, preserve human edits
                existing_tbl.table_type = tbl_type
                existing_tbl.row_count_approx = row_count
                existing_tbl.importance_score = importance_score
                existing_tbl.importance_level = importance_level
                existing_tbl.uses_effective_dating = has_effective_dating
                # Only set entity type or business name if not already set by human
                if not existing_tbl.business_name:
                    existing_tbl.business_name = HRMetadataMapper.generate_business_name(tbl_name)
                if not existing_tbl.business_entity or existing_tbl.business_entity == "OTHER":
                    existing_tbl.business_entity = entity_type
                schema_tbl = existing_tbl
            else:
                schema_tbl = SchemaTable(
                    database_id=database_id,
                    schema_name=raw_discovery.get("schema_name", "main"),
                    table_name=tbl_name,
                    table_type=tbl_type,
                    row_count_approx=row_count,
                    business_name=HRMetadataMapper.generate_business_name(tbl_name),
                    description=f"HR data entity representing {tbl_name.replace('_', ' ')} records.",
                    business_entity=entity_type,
                    importance_score=importance_score,
                    importance_level=importance_level,
                    uses_effective_dating=has_effective_dating,
                    status="AUTO_DISCOVERED"
                )
                self.db.add(schema_tbl)

            self.db.flush()
            discovered_tables_models.append(schema_tbl)

            # Map existing columns by name
            existing_cols = {c.column_name: c for c in schema_tbl.columns} if existing_tbl else {}

            # Process Columns
            fk_col_names = {c for fk in fks for c in fk.get("constrained_columns", [])}
            for col_meta in col_list:
                c_name = col_meta["name"]
                c_raw_type = col_meta["data_type"]
                c_is_pk = bool(col_meta["is_primary_key"])
                c_is_fk = c_name in fk_col_names
                c_is_null = bool(col_meta["is_nullable"])
                c_default = col_meta["default_value"]
                c_ord = col_meta["ordinal_position"]

                # Infer HR semantics
                semantics = HRMetadataMapper.classify_column_semantics(
                    column_name=c_name,
                    data_type=c_raw_type,
                    is_primary_key=c_is_pk,
                    is_foreign_key=c_is_fk
                )

                existing_col = existing_cols.get(c_name)
                if existing_col:
                    # Update technical properties, preserve human definitions and verification
                    existing_col.data_type = c_raw_type
                    existing_col.normalized_data_type = semantics["normalized_data_type"]
                    existing_col.is_primary_key = c_is_pk
                    existing_col.is_foreign_key = c_is_fk
                    existing_col.is_nullable = c_is_null
                    existing_col.default_value = c_default
                    existing_col.ordinal_position = c_ord
                    # If human hasn't verified/customized, enrich with defaults
                    if existing_col.status != "VERIFIED":
                        if not existing_col.business_name:
                            existing_col.business_name = HRMetadataMapper.generate_business_name(c_name)
                        if not existing_col.business_definition:
                            existing_col.business_definition = semantics["business_definition"]
                        if not existing_col.hr_concept:
                            existing_col.hr_concept = semantics["hr_concept"]
                        existing_col.is_metric = semantics["is_metric"]
                        existing_col.default_aggregation = semantics["default_aggregation"]
                        existing_col.is_dimension = semantics["is_dimension"]
                        existing_col.is_date_field = semantics["is_date_field"]
                        existing_col.date_role = semantics["date_role"]
                        existing_col.is_sensitive = semantics["is_sensitive"]
                        existing_col.sensitive_category = semantics["sensitive_category"]
                else:
                    new_col = SchemaColumn(
                        table_id=schema_tbl.id,
                        column_name=c_name,
                        business_name=HRMetadataMapper.generate_business_name(c_name),
                        description=f"{c_name} attribute of {tbl_name}.",
                        business_definition=semantics["business_definition"],
                        hr_concept=semantics["hr_concept"],
                        data_type=c_raw_type,
                        normalized_data_type=semantics["normalized_data_type"],
                        is_primary_key=c_is_pk,
                        is_foreign_key=c_is_fk,
                        is_nullable=c_is_null,
                        default_value=c_default,
                        ordinal_position=c_ord,
                        is_sensitive=semantics["is_sensitive"],
                        sensitive_category=semantics["sensitive_category"],
                        is_date_field=semantics["is_date_field"],
                        date_role=semantics["date_role"],
                        is_metric=semantics["is_metric"],
                        default_aggregation=semantics["default_aggregation"],
                        is_dimension=semantics["is_dimension"],
                        status="AUTO_DISCOVERED"
                    )
                    self.db.add(new_col)

            # Queue foreign key relationships for discovery
            for fk in fks:
                ref_tbl = fk.get("referred_table", "")
                src_cols = fk.get("constrained_columns", [])
                ref_cols = fk.get("referred_columns", [])
                if ref_tbl and src_cols and ref_cols:
                    relationships_to_create.append({
                        "source_table": tbl_name,
                        "source_column": src_cols[0],
                        "target_table": ref_tbl,
                        "target_column": ref_cols[0],
                        "relationship_type": "MANY_TO_ONE",
                        "relationship_source": "DATABASE_FOREIGN_KEY",
                        "confidence": "HIGH",
                        "join_condition": f"{tbl_name}.{src_cols[0]} = {ref_tbl}.{ref_cols[0]}"
                    })

            # Re-index/Constraints storage
            # Clean old indexes & constraints for this table
            self.db.query(SchemaIndex).filter_by(table_id=schema_tbl.id).delete()
            for idx_info in tbl.get("indexes", []):
                self.db.add(SchemaIndex(
                    table_id=schema_tbl.id,
                    index_name=idx_info.get("name", "idx"),
                    columns_json=idx_info.get("columns", []),
                    is_unique=idx_info.get("unique", False)
                ))

            self.db.query(SchemaConstraint).filter_by(table_id=schema_tbl.id).delete()
            for uc_info in tbl.get("constraints", []):
                self.db.add(SchemaConstraint(
                    table_id=schema_tbl.id,
                    constraint_name=uc_info.get("name", "uc"),
                    constraint_type=uc_info.get("type", "UNIQUE"),
                    definition=",".join(uc_info.get("columns", []))
                ))

        self.db.flush()

        # 7. Add Inferred Joins from Module 2 (if not already covered by FK)
        existing_fk_pairs = {
            (r["source_table"].lower(), r["target_table"].lower())
            for r in relationships_to_create
        }
        for inf in inferred_joins:
            pair = (inf["source_table"].lower(), inf["target_table"].lower())
            rev_pair = (inf["target_table"].lower(), inf["source_table"].lower())
            if pair not in existing_fk_pairs and rev_pair not in existing_fk_pairs:
                relationships_to_create.append({
                    "source_table": inf["source_table"],
                    "source_column": inf["source_column"],
                    "target_table": inf["target_table"],
                    "target_column": inf["target_column"],
                    "relationship_type": "MANY_TO_ONE",
                    "relationship_source": "SQL_USAGE",
                    "confidence": inf["confidence"],
                    "usage_count": inf["usage_count"],
                    "join_condition": inf["join_condition"]
                })

        # Persist Relationships (Preserving MANUAL relationships)
        tbl_lookup = {
            t.table_name.lower(): t
            for t in self.db.query(SchemaTable).filter_by(database_id=database_id).all()
        }
        col_lookup = {
            (c.table.table_name.lower(), c.column_name.lower()): c
            for c in self.db.query(SchemaColumn)
            .join(SchemaTable)
            .filter(SchemaTable.database_id == database_id)
            .all()
        }

        # Remove previous non-manual relationships to avoid duplicates on refresh
        self.db.query(SchemaRelationship).filter(
            SchemaRelationship.database_id == database_id,
            SchemaRelationship.relationship_source.in_(["DATABASE_FOREIGN_KEY", "SQL_USAGE"])
        ).delete(synchronize_session=False)

        persisted_relationships = []
        for rel in relationships_to_create:
            src_t = tbl_lookup.get(rel["source_table"].lower())
            tgt_t = tbl_lookup.get(rel["target_table"].lower())
            if src_t and tgt_t:
                src_c = col_lookup.get((rel["source_table"].lower(), rel["source_column"].lower()))
                tgt_c = col_lookup.get((rel["target_table"].lower(), rel["target_column"].lower()))

                new_rel = SchemaRelationship(
                    database_id=database_id,
                    source_table_id=src_t.id,
                    source_table_name=src_t.table_name,
                    source_column_id=src_c.id if src_c else None,
                    source_column_name=rel["source_column"],
                    target_table_id=tgt_t.id,
                    target_table_name=tgt_t.table_name,
                    target_column_id=tgt_c.id if tgt_c else None,
                    target_column_name=rel["target_column"],
                    relationship_type=rel.get("relationship_type", "MANY_TO_ONE"),
                    relationship_source=rel.get("relationship_source", "DATABASE_FOREIGN_KEY"),
                    confidence=rel.get("confidence", "HIGH"),
                    usage_count=rel.get("usage_count", 1),
                    join_condition_sql=rel.get("join_condition"),
                    is_verified=False
                )
                self.db.add(new_rel)
                persisted_relationships.append(new_rel)

        self.db.flush()

        # 8. Snapshot & Drift Detection
        snapshot_mgr = SchemaSnapshotManager(self.db)
        canonical_snapshot = snapshot_mgr.build_canonical_snapshot(
            database_id=database_id,
            tables_data=raw_discovery.get("tables", []),
            relationships_data=relationships_to_create
        )
        schema_hash = SchemaSnapshotManager.compute_schema_hash(canonical_snapshot)
        snapshot, changes_detected = snapshot_mgr.create_snapshot(
            database_id=database_id,
            canonical_snapshot=canonical_snapshot,
            schema_hash=schema_hash,
            user_id=user_id
        )

        self.db.commit()

        # Compute summary metrics
        total_cols = sum(len(t.columns) for t in discovered_tables_models)
        sensitive_cols = (
            self.db.query(SchemaColumn)
            .join(SchemaTable)
            .filter(SchemaTable.database_id == database_id, SchemaColumn.is_sensitive == True)
            .count()
        )

        return {
            "success": True,
            "database_id": database_id,
            "dialect": dialect,
            "schema_hash": schema_hash,
            "snapshot_version": snapshot.version_number,
            "tables_discovered": len(discovered_tables_models),
            "columns_discovered": total_cols,
            "relationships_discovered": len(relationships_to_create),
            "sensitive_fields_count": sensitive_cols,
            "changes_detected_count": len(changes_detected),
            "changes_detected": changes_detected
        }

    def refresh_schema(self, database_id: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Re-inspects the database, updates metadata while preserving human edits, and returns changes."""
        return self.discover_schema(database_id=database_id, user_id=user_id)

    def get_schema_health(self, database_id: str) -> Dict[str, Any]:
        """Calculates schema completeness, verification percentage, and AI readiness score."""
        tables = self.db.query(SchemaTable).filter_by(database_id=database_id).all()
        table_count = len(tables)

        if table_count == 0:
            return {
                "health_score": 0.0,
                "readiness_status": "NOT_DISCOVERED",
                "table_count": 0,
                "column_count": 0,
                "relationship_count": 0,
                "verified_tables_pct": 0.0,
                "verified_columns_pct": 0.0,
                "described_tables_pct": 0.0,
                "sensitive_fields_count": 0,
                "views_count": 0
            }

        table_ids = [t.id for t in tables]
        columns = self.db.query(SchemaColumn).filter(SchemaColumn.table_id.in_(table_ids)).all()
        col_count = len(columns)

        views_count = sum(1 for t in tables if t.table_type == "VIEW")
        verified_tables = sum(1 for t in tables if t.status == "VERIFIED")
        described_tables = sum(1 for t in tables if t.description and len(t.description.strip()) > 0)

        verified_columns = sum(1 for c in columns if c.status == "VERIFIED")
        described_columns = sum(1 for c in columns if c.business_definition and len(c.business_definition.strip()) > 0)
        sensitive_count = sum(1 for c in columns if c.is_sensitive)

        rel_count = self.db.query(SchemaRelationship).filter_by(database_id=database_id).count()

        # Component scores
        table_desc_pct = round((described_tables / table_count) * 100, 1)
        col_desc_pct = round((described_columns / col_count) * 100, 1) if col_count > 0 else 0.0
        table_verify_pct = round((verified_tables / table_count) * 100, 1)
        col_verify_pct = round((verified_columns / col_count) * 100, 1) if col_count > 0 else 0.0
        rel_score = min(100.0, rel_count * 10.0)

        # Weighted Health Score:
        # Descriptions: 40% (20% table + 20% column)
        # Relationships: 30%
        # Verification: 30% (15% table + 15% column)
        health_score = round(
            (0.20 * table_desc_pct) +
            (0.20 * col_desc_pct) +
            (0.30 * rel_score) +
            (0.15 * table_verify_pct) +
            (0.15 * col_verify_pct),
            1
        )

        readiness = "EXCELLENT" if health_score >= 85 else ("GOOD" if health_score >= 65 else ("FAIR" if health_score >= 40 else "POOR"))

        return {
            "health_score": health_score,
            "readiness_status": readiness,
            "table_count": table_count,
            "views_count": views_count,
            "column_count": col_count,
            "relationship_count": rel_count,
            "verified_tables_count": verified_tables,
            "verified_tables_pct": table_verify_pct,
            "verified_columns_count": verified_columns,
            "verified_columns_pct": col_verify_pct,
            "described_tables_pct": table_desc_pct,
            "described_columns_pct": col_desc_pct,
            "sensitive_fields_count": sensitive_count
        }

    def get_tables(
        self,
        database_id: str,
        entity_type: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Lists tables for a database with filtering and stats."""
        query = self.db.query(SchemaTable).filter(SchemaTable.database_id == database_id)

        if entity_type and entity_type.upper() != "ALL":
            query = query.filter(SchemaTable.business_entity == entity_type.upper())
        if status and status.upper() != "ALL":
            query = query.filter(SchemaTable.status == status.upper())
        if search:
            term = f"%{search}%"
            query = query.filter(
                or_(
                    SchemaTable.table_name.ilike(term),
                    SchemaTable.business_name.ilike(term),
                    SchemaTable.description.ilike(term)
                )
            )

        tables = query.order_by(SchemaTable.importance_score.desc(), SchemaTable.table_name.asc()).all()

        results = []
        for t in tables:
            col_count = len(t.columns)
            pk_count = sum(1 for c in t.columns if c.is_primary_key)
            fk_count = sum(1 for c in t.columns if c.is_foreign_key)
            sensitive_count = sum(1 for c in t.columns if c.is_sensitive)

            results.append({
                "id": t.id,
                "table_name": t.table_name,
                "table_type": t.table_type,
                "business_name": t.business_name or t.table_name,
                "business_entity": t.business_entity,
                "description": t.description,
                "importance_score": t.importance_score,
                "importance_level": t.importance_level,
                "uses_effective_dating": t.uses_effective_dating,
                "status": t.status,
                "row_count_approx": t.row_count_approx,
                "column_count": col_count,
                "primary_keys_count": pk_count,
                "foreign_keys_count": fk_count,
                "sensitive_columns_count": sensitive_count,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            })
        return results

    def get_table_detail(self, table_id: int) -> Optional[Dict[str, Any]]:
        """Returns deep details of a table including its columns, relationships, indexes, and usage."""
        table = self.db.query(SchemaTable).filter_by(id=table_id).first()
        if not table:
            return None

        # Columns
        columns_data = []
        for c in table.columns:
            columns_data.append({
                "id": c.id,
                "column_name": c.column_name,
                "business_name": c.business_name or c.column_name,
                "description": c.description,
                "business_definition": c.business_definition,
                "hr_concept": c.hr_concept,
                "data_type": c.data_type,
                "normalized_data_type": c.normalized_data_type,
                "is_primary_key": c.is_primary_key,
                "is_foreign_key": c.is_foreign_key,
                "is_nullable": c.is_nullable,
                "default_value": c.default_value,
                "ordinal_position": c.ordinal_position,
                "is_sensitive": c.is_sensitive,
                "sensitive_category": c.sensitive_category,
                "is_date_field": c.is_date_field,
                "date_role": c.date_role,
                "is_metric": c.is_metric,
                "default_aggregation": c.default_aggregation,
                "is_dimension": c.is_dimension,
                "status": c.status
            })

        # Relationships
        out_rels = (
            self.db.query(SchemaRelationship)
            .filter_by(source_table_id=table.id)
            .all()
        )
        in_rels = (
            self.db.query(SchemaRelationship)
            .filter_by(target_table_id=table.id)
            .all()
        )

        relationships_data = []
        for r in out_rels:
            relationships_data.append({
                "id": r.id,
                "direction": "OUTGOING",
                "source_table": r.source_table_name,
                "source_column": r.source_column_name,
                "target_table": r.target_table_name,
                "target_column": r.target_column_name,
                "relationship_type": r.relationship_type,
                "relationship_source": r.relationship_source,
                "confidence": r.confidence,
                "usage_count": r.usage_count,
                "is_verified": r.is_verified,
                "join_condition": r.join_condition_sql
            })
        for r in in_rels:
            relationships_data.append({
                "id": r.id,
                "direction": "INCOMING",
                "source_table": r.source_table_name,
                "source_column": r.source_column_name,
                "target_table": r.target_table_name,
                "target_column": r.target_column_name,
                "relationship_type": r.relationship_type,
                "relationship_source": r.relationship_source,
                "confidence": r.confidence,
                "usage_count": r.usage_count,
                "is_verified": r.is_verified,
                "join_condition": r.join_condition_sql
            })

        # Indexes
        indexes_data = [
            {"name": idx.index_name, "columns": idx.columns_json, "unique": idx.is_unique}
            for idx in table.indexes
        ]

        # Constraints
        constraints_data = [
            {"name": cn.constraint_name, "type": cn.constraint_type, "definition": cn.definition}
            for cn in table.constraints
        ]

        # Usage metrics from Module 2
        usage_metric = (
            self.db.query(SchemaUsageMetric)
            .filter_by(database_id=table.database_id, entity_type="TABLE", entity_name=table.table_name.lower())
            .first()
        )
        query_usage_count = usage_metric.query_count if usage_metric else 0

        return {
            "id": table.id,
            "database_id": table.database_id,
            "schema_name": table.schema_name,
            "table_name": table.table_name,
            "table_type": table.table_type,
            "business_name": table.business_name,
            "description": table.description,
            "business_entity": table.business_entity,
            "importance_score": table.importance_score,
            "importance_level": table.importance_level,
            "uses_effective_dating": table.uses_effective_dating,
            "status": table.status,
            "row_count_approx": table.row_count_approx,
            "query_usage_count": query_usage_count,
            "columns": columns_data,
            "relationships": relationships_data,
            "indexes": indexes_data,
            "constraints": constraints_data
        }

    def update_table_metadata(
        self,
        table_id: int,
        data: Dict[str, Any],
        user_id: Optional[int] = None
    ) -> Optional[SchemaTable]:
        """Allows humans/admins to edit business name, description, and entity type."""
        table = self.db.query(SchemaTable).filter_by(id=table_id).first()
        if not table:
            return None

        if "business_name" in data and data["business_name"] is not None:
            table.business_name = data["business_name"]
        if "description" in data and data["description"] is not None:
            table.description = data["description"]
        if "business_entity" in data and data["business_entity"] is not None:
            table.business_entity = data["business_entity"].upper()
        if "status" in data and data["status"] is not None:
            table.status = data["status"].upper()
            if table.status == "VERIFIED":
                table.verified_by_id = user_id
                table.verified_at = datetime.datetime.utcnow()

        self.db.commit()
        self.db.refresh(table)
        return table

    def update_column_metadata(
        self,
        column_id: int,
        data: Dict[str, Any],
        user_id: Optional[int] = None
    ) -> Optional[SchemaColumn]:
        """Allows humans to edit column business name, definition, sensitivity, and metric roles."""
        col = self.db.query(SchemaColumn).filter_by(id=column_id).first()
        if not col:
            return None

        fields = [
            "business_name", "description", "business_definition", "hr_concept",
            "is_sensitive", "sensitive_category", "is_date_field", "date_role",
            "is_metric", "default_aggregation", "is_dimension", "status"
        ]
        for f in fields:
            if f in data and data[f] is not None:
                setattr(col, f, data[f])

        self.db.commit()
        self.db.refresh(col)
        return col

    def verify_table(self, table_id: int, user_id: Optional[int] = None) -> Optional[SchemaTable]:
        """Marks table and all its columns as VERIFIED."""
        table = self.db.query(SchemaTable).filter_by(id=table_id).first()
        if not table:
            return None

        table.status = "VERIFIED"
        table.verified_by_id = user_id
        table.verified_at = datetime.datetime.utcnow()

        for c in table.columns:
            c.status = "VERIFIED"

        self.db.commit()
        self.db.refresh(table)
        return table

    def verify_column(self, column_id: int, user_id: Optional[int] = None) -> Optional[SchemaColumn]:
        """Marks an individual column as VERIFIED."""
        col = self.db.query(SchemaColumn).filter_by(id=column_id).first()
        if not col:
            return None

        col.status = "VERIFIED"
        self.db.commit()
        self.db.refresh(col)
        return col

    def get_relationships(
        self,
        database_id: str,
        source: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Lists relationships across database tables with optional source filter."""
        query = self.db.query(SchemaRelationship).filter(SchemaRelationship.database_id == database_id)
        if source and source.upper() != "ALL":
            query = query.filter(SchemaRelationship.relationship_source == source.upper())

        rels = query.all()
        return [
            {
                "id": r.id,
                "database_id": r.database_id,
                "source_table": r.source_table_name,
                "source_column": r.source_column_name,
                "target_table": r.target_table_name,
                "target_column": r.target_column_name,
                "relationship_type": r.relationship_type,
                "relationship_source": r.relationship_source,
                "confidence": r.confidence,
                "usage_count": r.usage_count,
                "join_condition": r.join_condition_sql,
                "is_verified": r.is_verified,
            }
            for r in rels
        ]

    def add_manual_relationship(
        self,
        database_id: str,
        data: Dict[str, Any],
        user_id: Optional[int] = None
    ) -> SchemaRelationship:
        """Allows administrator to define a custom join link between tables."""
        src_tbl = self.db.query(SchemaTable).filter_by(database_id=database_id, table_name=data["source_table"]).first()
        tgt_tbl = self.db.query(SchemaTable).filter_by(database_id=database_id, table_name=data["target_table"]).first()

        if not src_tbl or not tgt_tbl:
            raise ValueError(f"Source or target table not found in database {database_id}")

        src_col = (
            self.db.query(SchemaColumn)
            .filter_by(table_id=src_tbl.id, column_name=data["source_column"])
            .first()
        )
        tgt_col = (
            self.db.query(SchemaColumn)
            .filter_by(table_id=tgt_tbl.id, column_name=data["target_column"])
            .first()
        )

        rel = SchemaRelationship(
            database_id=database_id,
            source_table_id=src_tbl.id,
            source_table_name=src_tbl.table_name,
            source_column_id=src_col.id if src_col else None,
            source_column_name=data["source_column"],
            target_table_id=tgt_tbl.id,
            target_table_name=tgt_tbl.table_name,
            target_column_id=tgt_col.id if tgt_col else None,
            target_column_name=data["target_column"],
            relationship_type=data.get("relationship_type", "MANY_TO_ONE"),
            relationship_source="MANUAL",
            confidence="HIGH",
            usage_count=1,
            join_condition_sql=f"{src_tbl.table_name}.{data['source_column']} = {tgt_tbl.table_name}.{data['target_column']}",
            is_verified=True
        )
        self.db.add(rel)
        self.db.commit()
        self.db.refresh(rel)
        return rel

    def delete_manual_relationship(self, relationship_id: int) -> bool:
        """Deletes a manually created relationship."""
        rel = (
            self.db.query(SchemaRelationship)
            .filter_by(id=relationship_id, relationship_source="MANUAL")
            .first()
        )
        if not rel:
            return False
        self.db.delete(rel)
        self.db.commit()
        return True

    def get_schema_changes(self, database_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves recent schema drift and change history."""
        changes = (
            self.db.query(SchemaChange)
            .filter(SchemaChange.database_id == database_id)
            .order_by(SchemaChange.detected_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": c.id,
                "database_id": c.database_id,
                "snapshot_id": c.snapshot_id,
                "change_type": c.change_type,
                "target_name": c.target_name,
                "details": c.details_json,
                "detected_at": c.detected_at.isoformat() if c.detected_at else None
            }
            for c in changes
        ]

    def get_snapshots(self, database_id: str) -> List[Dict[str, Any]]:
        """Lists historical snapshots for a database."""
        snapshots = (
            self.db.query(SchemaSnapshot)
            .filter_by(database_id=database_id)
            .order_by(SchemaSnapshot.version_number.desc())
            .all()
        )
        return [
            {
                "id": s.id,
                "version_number": s.version_number,
                "schema_hash": s.schema_hash,
                "table_count": s.table_count,
                "column_count": s.column_count,
                "relationship_count": s.relationship_count,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in snapshots
        ]

    def get_usage_metrics(self, database_id: str) -> Dict[str, Any]:
        """Retrieves table, column, and join query frequencies mined from Module 2."""
        metrics = (
            self.db.query(SchemaUsageMetric)
            .filter_by(database_id=database_id)
            .order_by(SchemaUsageMetric.query_count.desc())
            .all()
        )
        tables = [m for m in metrics if m.entity_type == "TABLE"]
        columns = [m for m in metrics if m.entity_type == "COLUMN"]
        joins = [m for m in metrics if m.entity_type == "JOIN"]

        return {
            "top_tables": [{"name": m.entity_name, "count": m.query_count} for m in tables[:10]],
            "top_columns": [{"name": m.entity_name, "count": m.query_count} for m in columns[:15]],
            "top_joins": [{"name": m.entity_name, "count": m.query_count} for m in joins[:10]],
        }

    def search_schema(self, database_id: str, query_term: str) -> Dict[str, Any]:
        """Searches tables and columns across technical names, business names, definitions, and concepts."""
        term = f"%{query_term}%"

        matching_tables = (
            self.db.query(SchemaTable)
            .filter(
                SchemaTable.database_id == database_id,
                or_(
                    SchemaTable.table_name.ilike(term),
                    SchemaTable.business_name.ilike(term),
                    SchemaTable.description.ilike(term),
                    SchemaTable.business_entity.ilike(term)
                )
            )
            .all()
        )

        matching_columns = (
            self.db.query(SchemaColumn)
            .join(SchemaTable)
            .filter(
                SchemaTable.database_id == database_id,
                or_(
                    SchemaColumn.column_name.ilike(term),
                    SchemaColumn.business_name.ilike(term),
                    SchemaColumn.business_definition.ilike(term),
                    SchemaColumn.hr_concept.ilike(term)
                )
            )
            .all()
        )

        return {
            "query": query_term,
            "matching_tables_count": len(matching_tables),
            "matching_columns_count": len(matching_columns),
            "tables": [
                {
                    "id": t.id,
                    "table_name": t.table_name,
                    "business_name": t.business_name,
                    "business_entity": t.business_entity,
                    "importance_level": t.importance_level
                }
                for t in matching_tables
            ],
            "columns": [
                {
                    "id": c.id,
                    "table_name": c.table.table_name,
                    "column_name": c.column_name,
                    "business_name": c.business_name,
                    "hr_concept": c.hr_concept,
                    "is_sensitive": c.is_sensitive,
                    "data_type": c.data_type
                }
                for c in matching_columns
            ]
        }
