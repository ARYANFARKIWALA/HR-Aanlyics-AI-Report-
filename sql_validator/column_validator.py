"""Column-level security, wildcard (SELECT *) enforcement, and column expansion."""

from sqlalchemy.orm import Session
from sqlglot import exp

from backend.auth.authorization import AuthorizationService
from backend.database.models import User

from .schemas import ChecklistItem


class ColumnValidator:
    """Enforces SELECT * policies and Column-Level Security (CLS) access rules."""

    @staticmethod
    def validate_select_star(
        expression: exp.Expression,
        allow_select_star: bool = False
    ) -> tuple[bool, list[ChecklistItem], list[str], list[str]]:
        """Checks for wildcard projections (SELECT *)."""
        checklist = []
        violations = []
        warnings = []

        has_star = False
        for s in expression.find_all(exp.Star):
            has_star = True
            break

        if has_star:
            if not allow_select_star:
                checklist.append(ChecklistItem(
                    check_name="explicit_column_projection",
                    passed=False,
                    severity="WARNING",
                    details="Unconstrained 'SELECT *' detected. Explicit column projection is recommended."
                ))
                warnings.append("SELECT * projection detected. Explicit column listing improves security and efficiency.")
            else:
                checklist.append(ChecklistItem(
                    check_name="explicit_column_projection",
                    passed=True,
                    severity="INFO",
                    details="Wildcard projection allowed by policy override."
                ))
        else:
            checklist.append(ChecklistItem(
                check_name="explicit_column_projection",
                passed=True,
                severity="INFO",
                details="Explicit column projections verified."
            ))

        return True, checklist, violations, warnings

    @staticmethod
    def validate_column_permissions(
        expression: exp.Expression,
        db: Session,
        user: User | None,
        database_id: str,
        referenced_tables: set[str]
    ) -> tuple[bool, list[ChecklistItem], list[str]]:
        """Verifies that user is permitted to query the selected columns under CLS."""
        checklist = []
        violations = []

        if not user or user.role == "admin":
            checklist.append(ChecklistItem(
                check_name="column_level_security",
                passed=True,
                severity="INFO",
                details="Admin bypass or unrestricted column access."
            ))
            return True, checklist, violations

        forbidden_cols = set()
        for tbl in referenced_tables:
            cls_rules = AuthorizationService.get_column_permissions(db, user, database_id, tbl)
            for col in expression.find_all(exp.Column):
                col_name = col.name.lower()
                rule = cls_rules.get(col_name)
                if rule and not rule.get("is_allowed", True):
                    forbidden_cols.add(f"{tbl}.{col_name}")

        if forbidden_cols:
            checklist.append(ChecklistItem(
                check_name="column_level_security",
                passed=False,
                severity="BLOCKER",
                details=f"User role '{user.role}' is not authorized to query restricted columns: {sorted(forbidden_cols)}"
            ))
            violations.append(f"Column-Level Security violation: Access denied to column(s) {sorted(forbidden_cols)}.")
            return False, checklist, violations

        checklist.append(ChecklistItem(
            check_name="column_level_security",
            passed=True,
            severity="INFO",
            details="All requested columns cleared by Column-Level Security."
        ))
        return True, checklist, violations
