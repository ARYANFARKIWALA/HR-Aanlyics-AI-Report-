"""Join validator detecting Cartesian products and excessive join complexity."""

from typing import Tuple, List
import sqlglot
from sqlglot import exp
from .schemas import ChecklistItem


class JoinValidator:
    """Detects Cartesian joins and excessive join depth."""

    @staticmethod
    def validate(
        expression: exp.Expression,
        max_joins: int = 5,
        disallow_cartesian: bool = True
    ) -> Tuple[bool, List[ChecklistItem], List[str], List[str]]:
        checklist = []
        violations = []
        warnings = []

        # 1. Count Joins
        joins = list(expression.find_all(exp.Join))
        join_count = len(joins)

        if join_count > max_joins:
            checklist.append(ChecklistItem(
                check_name="join_count_limit",
                passed=False,
                severity="WARNING",
                details=f"Query contains {join_count} JOIN operations (Threshold: {max_joins})."
            ))
            warnings.append(f"High join complexity: {join_count} joins detected (recommended limit: {max_joins}).")
        else:
            checklist.append(ChecklistItem(
                check_name="join_count_limit",
                passed=True,
                severity="INFO",
                details=f"Join count ({join_count}) within permitted threshold ({max_joins})."
            ))

        # 2. Check for Cartesian / Cross Joins
        cartesian_detected = False
        for j in joins:
            # Check for explicit CROSS JOIN
            if j.kind and "CROSS" in str(j.kind).upper():
                cartesian_detected = True
                break

            # Check for JOIN without ON or USING clause
            if not j.args.get("on") and not j.args.get("using"):
                # Natural join or cross join
                cartesian_detected = True
                break

        # Check for comma join with multiple tables in FROM without WHERE
        from_node = expression.args.get("from")
        if from_node:
            expressions = from_node.expressions or []
            if len(expressions) > 1 and not expression.args.get("where"):
                cartesian_detected = True

        if cartesian_detected:
            checklist.append(ChecklistItem(
                check_name="cartesian_join_check",
                passed=False,
                severity="BLOCKER" if disallow_cartesian else "WARNING",
                details="Cartesian join / unconditioned cross join detected."
            ))
            if disallow_cartesian:
                violations.append("Cartesian product (CROSS JOIN / unconditional join) is strictly forbidden due to runaway memory/CPU risk.")
                return False, checklist, violations, warnings
            else:
                warnings.append("Cartesian product detected. Ensure this is intentional.")
        else:
            checklist.append(ChecklistItem(
                check_name="cartesian_join_check",
                passed=True,
                severity="INFO",
                details="All joins have explicit ON or USING conditions. No Cartesian products."
            ))

        return True, checklist, violations, warnings
