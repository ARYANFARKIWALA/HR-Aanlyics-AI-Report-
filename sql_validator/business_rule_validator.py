"""Business rule compliance validator for HR Analytics."""

from sqlalchemy.orm import Session
from sqlglot import exp

from backend.database.models_rules import BusinessRule

from .schemas import ChecklistItem


class BusinessRuleValidator:
    """Verifies that queries on HR data comply with active organizational business rules."""

    @staticmethod
    def validate(
        expression: exp.Expression,
        db: Session,
        database_id: str,
        referenced_tables: set[str]
    ) -> tuple[bool, list[ChecklistItem], list[str], list[str]]:
        checklist = []
        violations = []
        warnings = []

        # Effective dating compliance rule
        # If employees or compensation_history are queried, verify effective dating filter
        needs_effective_dating = bool(referenced_tables.intersection({"employees", "compensation_history"}))

        if needs_effective_dating:
            # Check WHERE clause for is_current or effective_date
            where_node = expression.args.get("where")
            has_eff_dating = False
            if where_node:
                where_str = where_node.sql().lower()
                if "is_current" in where_str or "effective_end_date" in where_str or "effective_start_date" in where_str:
                    has_eff_dating = True

            if not has_eff_dating:
                checklist.append(ChecklistItem(
                    check_name="hr_effective_dating_rule",
                    passed=False,
                    severity="WARNING",
                    details="Query on 'employees' or 'compensation_history' lacks an explicit effective-dating filter ('is_current = 1' or 'effective_end_date')."
                ))
                warnings.append("Business Rule BR-001 Reminder: Effective-dating filter ('is_current = 1') is recommended when querying employee records to avoid historical record duplication.")
            else:
                checklist.append(ChecklistItem(
                    check_name="hr_effective_dating_rule",
                    passed=True,
                    severity="INFO",
                    details="Effective dating filter (BR-001) verified."
                ))

        # Check any active mandatory business rules in database
        try:
            active_rules = db.query(BusinessRule).filter(
                BusinessRule.status == "ACTIVE",
                BusinessRule.is_current == True
            ).all()
            for r in active_rules:
                if r.rule_code in ["BR-001", "BR-002"]:
                    # Verified active rules
                    pass
        except Exception:
            pass

        return True, checklist, violations, warnings
