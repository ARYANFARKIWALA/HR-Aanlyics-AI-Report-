"""Module 4: Business Rule Conflict Detector.

Detects contradictory logic between business rules, such as:
- Contradictory values on identical columns (e.g. status = 'ACTIVE' vs status = 'INACTIVE')
- Incompatible date filters
- IS NULL vs IS NOT NULL contradictions
"""

import re
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend.database.models_rules import BusinessRule

logger = logging.getLogger("business_rules.conflict")


class RuleConflictDetector:
    """Scans for logical contradictions across active rules."""

    @classmethod
    def detect_conflicts(
        cls,
        candidate_rule: Dict[str, Any],
        db: Session,
        database_id: Optional[str] = None,
        exclude_rule_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Compares a candidate rule against currently active rules for contradictions."""
        db_id = candidate_rule.get("database_id") or database_id or "sqlite_hr_default"
        table_name = (candidate_rule.get("table_name") or "").lower().strip()
        column_name = (candidate_rule.get("column_name") or "").lower().strip()
        cand_expr = (candidate_rule.get("rule_expression") or "").strip()

        # Query other active rules for the same database
        query = db.query(BusinessRule).filter(
            BusinessRule.database_id == db_id,
            BusinessRule.status == "ACTIVE",
            BusinessRule.is_current == True
        )
        if exclude_rule_id:
            query = query.filter(BusinessRule.id != exclude_rule_id)

        existing_rules = query.all()
        conflicts = []

        cand_col, cand_op, cand_val = cls._extract_predicate_parts(cand_expr)

        for rule in existing_rules:
            # 1. Check same table/column predicate contradiction
            r_col, r_op, r_val = cls._extract_predicate_parts(rule.rule_expression)

            # Match column targets
            same_col = False
            if cand_col and r_col and cand_col == r_col:
                same_col = True
            elif table_name and rule.table_name and table_name == rule.table_name.lower():
                if column_name and rule.column_name and column_name == rule.column_name.lower():
                    same_col = True

            if same_col and cand_op and r_op:
                # Contradictory equality: col = 'ACTIVE' vs col = 'INACTIVE' or col = 'A'
                if cand_op == "=" and r_op == "=" and cand_val != r_val:
                    conflicts.append({
                        "conflicting_rule_id": rule.id,
                        "conflicting_rule_code": rule.rule_code,
                        "conflicting_rule_name": rule.rule_name,
                        "conflicting_expression": rule.rule_expression,
                        "candidate_expression": cand_expr,
                        "conflict_type": "CONTRADICTORY_VALUE",
                        "reason": f"Column '{cand_col or column_name}' cannot simultaneously equal '{cand_val}' and '{r_val}'."
                    })

                # IS NULL vs IS NOT NULL
                elif (cand_op == "IS NULL" and r_op == "IS NOT NULL") or (cand_op == "IS NOT NULL" and r_op == "IS NULL"):
                    conflicts.append({
                        "conflicting_rule_id": rule.id,
                        "conflicting_rule_code": rule.rule_code,
                        "conflicting_rule_name": rule.rule_name,
                        "conflicting_expression": rule.rule_expression,
                        "candidate_expression": cand_expr,
                        "conflict_type": "NULLABILITY_CONTRADICTION",
                        "reason": f"Predicates contradict on nullability for column '{cand_col or column_name}'."
                    })

        return conflicts

    @classmethod
    def _extract_predicate_parts(cls, expr: str) -> (Optional[str], Optional[str], Optional[str]):
        """Extracts column, operator, and value from simple equality or null predicates."""
        clean = expr.strip()

        # IS NULL / IS NOT NULL
        m_null = re.match(r"^([\w\.]+)\s+IS\s+(NOT\s+NULL|NULL)", clean, re.IGNORECASE)
        if m_null:
            col = m_null.group(1).split(".")[-1].lower()
            op = f"IS {m_null.group(2).upper()}"
            return col, op, None

        # Equality: col = 'VAL' or col = VAL
        m_eq = re.match(r"^([\w\.]+)\s*(=|!=|<>)\s*['\"]?([^'\"]+)['\"]?", clean)
        if m_eq:
            col = m_eq.group(1).split(".")[-1].lower()
            op = m_eq.group(2)
            val = m_eq.group(3).strip()
            return col, op, val

        return None, None, None
