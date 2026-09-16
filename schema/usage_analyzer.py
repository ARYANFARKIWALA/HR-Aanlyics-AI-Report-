"""Module 3: Schema Usage Analyzer.

Analyzes SQL query patterns from Module 2's SQL repository to:
1. Count table, column, and join usage frequencies.
2. Infer recurring joins as SQL_USAGE relationships with confidence scores.
3. Compute table importance scores and importance levels based on query centrality.
"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from backend.database.models_repo import SQLReport
from backend.database.models_schema import (
    SchemaUsageMetric,
)

logger = logging.getLogger("schema.usage_analyzer")


class SchemaUsageAnalyzer:
    """Mines Module 2 SQL repository reports for query patterns, join graphs, and usage metrics."""

    def __init__(self, db: Session):
        self.db = db

    def analyze_repository_usage(self, database_id: str) -> dict[str, Any]:
        """Analyzes all active/approved reports for a database_id and computes usage frequencies.

        Returns:
            Dictionary with:
            - table_usage: Dict[table_name, count]
            - column_usage: Dict[f"{table}.{col}", count]
            - joins_usage: List[Dict[source_tbl, source_col, target_tbl, target_col, count]]
        """
        # Fetch reports associated with this database_id
        reports = (
            self.db.query(SQLReport)
            .filter(
                SQLReport.database_id == database_id,
                SQLReport.status.in_(["APPROVED", "VALID", "PENDING_REVIEW", "DRAFT"])
            )
            .all()
        )

        table_counts: dict[str, int] = {}
        column_counts: dict[str, int] = {}
        join_patterns: dict[tuple[str, str, str, str], int] = {}

        for r in reports:
            meta = r.metadata_rel
            if not meta:
                continue

            # 1. Table references
            # meta.tables is typically stored in SQLReportMetadata (via SQLGlot extraction)
            tables_list = []
            if hasattr(meta, "tables_json") and meta.tables_json:
                tables_list = meta.tables_json
            elif hasattr(meta, "tables") and meta.tables:
                tables_list = meta.tables if isinstance(meta.tables, list) else []

            # Also check if raw query tables were captured
            for tbl in tables_list:
                t_clean = tbl.lower().strip()
                table_counts[t_clean] = table_counts.get(t_clean, 0) + 1

            # 2. Column references
            cols_list = []
            if hasattr(meta, "columns_json") and meta.columns_json:
                cols_list = meta.columns_json
            elif hasattr(meta, "columns") and meta.columns:
                cols_list = meta.columns if isinstance(meta.columns, list) else []

            for col in cols_list:
                c_clean = col.lower().strip()
                column_counts[c_clean] = column_counts.get(c_clean, 0) + 1

            # 3. Join patterns
            joins_list = []
            if hasattr(meta, "joins_json") and meta.joins_json:
                joins_list = meta.joins_json
            elif hasattr(meta, "joins") and meta.joins:
                joins_list = meta.joins if isinstance(meta.joins, list) else []

            for j in joins_list:
                if isinstance(j, dict):
                    left_tbl = j.get("left_table", "").lower()
                    right_tbl = j.get("right_table", "").lower()
                    left_col = j.get("left_column", "").lower()
                    right_col = j.get("right_column", "").lower()

                    if left_tbl and right_tbl:
                        key = (left_tbl, left_col or "id", right_tbl, right_col or "id")
                        join_patterns[key] = join_patterns.get(key, 0) + 1

        # Save/Update SchemaUsageMetric records in DB
        self._record_usage_metrics(database_id, table_counts, column_counts, join_patterns)

        # Structure join results
        inferred_joins = []
        for (src_tbl, src_col, tgt_tbl, tgt_col), count in join_patterns.items():
            confidence = "HIGH" if count >= 3 else ("MEDIUM" if count == 2 else "LOW")
            inferred_joins.append({
                "source_table": src_tbl,
                "source_column": src_col,
                "target_table": tgt_tbl,
                "target_column": tgt_col,
                "usage_count": count,
                "confidence": confidence,
                "relationship_source": "SQL_USAGE",
                "join_condition": f"{src_tbl}.{src_col} = {tgt_tbl}.{tgt_col}"
            })

        return {
            "database_id": database_id,
            "total_reports_analyzed": len(reports),
            "table_usage": table_counts,
            "column_usage": column_counts,
            "inferred_joins": inferred_joins
        }

    def _record_usage_metrics(
        self,
        database_id: str,
        table_counts: dict[str, int],
        column_counts: dict[str, int],
        join_patterns: dict[tuple[str, str, str, str], int]
    ):
        """Persists aggregated usage metrics into schema_usage_metrics table."""
        try:
            # Record Table counts
            for tbl, count in table_counts.items():
                metric = (
                    self.db.query(SchemaUsageMetric)
                    .filter_by(database_id=database_id, entity_type="TABLE", entity_name=tbl)
                    .first()
                )
                if metric:
                    metric.query_count = count
                else:
                    self.db.add(SchemaUsageMetric(
                        database_id=database_id,
                        entity_type="TABLE",
                        entity_name=tbl,
                        query_count=count
                    ))

            # Record Column counts
            for col, count in column_counts.items():
                metric = (
                    self.db.query(SchemaUsageMetric)
                    .filter_by(database_id=database_id, entity_type="COLUMN", entity_name=col)
                    .first()
                )
                if metric:
                    metric.query_count = count
                else:
                    self.db.add(SchemaUsageMetric(
                        database_id=database_id,
                        entity_type="COLUMN",
                        entity_name=col,
                        query_count=count
                    ))

            # Record Join counts
            for (src_tbl, src_col, tgt_tbl, tgt_col), count in join_patterns.items():
                join_name = f"{src_tbl}->{tgt_tbl}"
                metric = (
                    self.db.query(SchemaUsageMetric)
                    .filter_by(database_id=database_id, entity_type="JOIN", entity_name=join_name)
                    .first()
                )
                if metric:
                    metric.query_count = count
                else:
                    self.db.add(SchemaUsageMetric(
                        database_id=database_id,
                        entity_type="JOIN",
                        entity_name=join_name,
                        query_count=count
                    ))

            self.db.flush()
        except Exception as e:
            logger.warning(f"Error persisting schema usage metrics: {e}")

    @classmethod
    def calculate_table_importance(
        cls,
        table_name: str,
        entity_type: str,
        column_count: int,
        fk_count: int,
        query_usage_count: int
    ) -> tuple[float, str]:
        """Calculates a normalized 0-100 table importance score and categorical level.

        Formula components:
        - Base weight for HR core entities (EMPLOYEE, DEPARTMENT): +25
        - Structural connectivity (Foreign keys / references): +5 per FK (up to +20)
        - Column density (richness): +1 per column (up to +15)
        - Historical SQL query usage: +8 per report query reference (up to +40)
        """
        score = 20.0  # Base floor

        # Entity weight
        if entity_type in ["EMPLOYEE", "DEPARTMENT"]:
            score += 25.0
        elif entity_type in ["COMPENSATION", "PERFORMANCE", "LEAVE_ATTENDANCE"]:
            score += 20.0
        elif entity_type in ["JOB_POSITION", "PAYROLL"]:
            score += 15.0

        # Structural FK connectivity
        score += min(20.0, fk_count * 5.0)

        # Column richness
        score += min(15.0, column_count * 1.0)

        # Query usage weight
        score += min(40.0, query_usage_count * 8.0)

        # Clamp to [0, 100]
        final_score = round(min(100.0, max(0.0, score)), 1)

        if final_score >= 80.0:
            level = "CRITICAL"
        elif final_score >= 60.0:
            level = "HIGH"
        elif final_score >= 40.0:
            level = "MEDIUM"
        else:
            level = "LOW"

        return final_score, level
