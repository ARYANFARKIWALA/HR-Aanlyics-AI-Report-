"""Risk scoring engine computing numerical risk scores and risk categories."""

from typing import Tuple, List, Set
from .schemas import ComplexityMetrics, ChecklistItem
from .policy_engine import LARGE_TABLES


class RiskEngine:
    """Computes transparent numeric risk scores and determines approval status."""

    @staticmethod
    def calculate_risk(
        violations: List[str],
        warnings: List[str],
        complexity: ComplexityMetrics,
        referenced_tables: Set[str],
        has_where: bool,
        has_limit: bool,
        user_role: str = "admin",
        max_risk_score_auto_approval: float = 65.0
    ) -> Tuple[float, str, str]:
        """
        Returns:
            (risk_score, risk_level, status)
        """
        # If any fatal violation occurred -> CRITICAL / REJECTED
        if violations:
            return 100.0, "CRITICAL", "REJECTED"

        # Base score from AST complexity
        score = complexity.estimated_complexity_score * 0.4

        # Risk penalty: Querying large tables without WHERE filter
        if referenced_tables.intersection(LARGE_TABLES) and not has_where:
            score += 25.0

        # Risk penalty: No LIMIT clause on broad table queries
        if not has_limit and not has_where:
            score += 15.0

        # Risk penalty for each warning
        score += min(len(warnings) * 5.0, 20.0)

        score = round(min(score, 99.0), 1)

        # Categorize
        if score < 30.0:
            risk_level = "LOW"
            status = "APPROVED"
        elif score < 65.0:
            risk_level = "MEDIUM"
            status = "APPROVED"
        else:
            risk_level = "HIGH"
            # High risk queries require manual approval unless run by admin
            status = "APPROVED" if user_role == "admin" else "REQUIRES_APPROVAL"

        return score, risk_level, status
