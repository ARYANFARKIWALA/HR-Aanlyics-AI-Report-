"""Module 6: SQL Knowledge Traceability & Audit Mapper.

Maps generated SQL clauses back to:
- Source Module 4 Business Rules
- Source Module 2 SQL Reports
- Schema Column & Table definitions
"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from backend.database.models_repo import SQLReport
from backend.database.models_rules import BusinessRule

logger = logging.getLogger("text_to_sql.traceability")


class SQLTraceabilityMapper:
    """Provides complete audit trail mapping SQL expressions to organizational knowledge."""

    def __init__(self, db: Session):
        self.db = db

    def map_traceability(
        self,
        applied_rule_ids: list[int],
        reused_report_id: int | None = None
    ) -> dict[str, Any]:
        """Collects metadata for all rules and reports linked to generated SQL."""
        rules_metadata = []
        if applied_rule_ids:
            rules = self.db.query(BusinessRule).filter(BusinessRule.id.in_(applied_rule_ids)).all()
            for r in rules:
                rules_metadata.append({
                    "rule_id": r.id,
                    "rule_code": r.rule_code,
                    "rule_name": r.rule_name,
                    "rule_type": r.rule_type,
                    "rule_expression": r.rule_expression,
                    "natural_language_rule": r.natural_language_rule,
                    "priority": r.priority,
                    "status": r.status
                })

        reports_metadata = []
        if reused_report_id:
            rpt = self.db.query(SQLReport).filter_by(id=reused_report_id).first()
            if rpt:
                reports_metadata.append({
                    "report_id": rpt.id,
                    "report_code": rpt.report_code,
                    "report_name": rpt.report_name,
                    "category": rpt.category,
                    "description": rpt.description
                })

        return {
            "applied_rules": rules_metadata,
            "reused_reports": reports_metadata
        }
