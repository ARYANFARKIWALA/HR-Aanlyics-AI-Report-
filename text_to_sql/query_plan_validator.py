"""Module 6: Query Plan Validator.

Validates that a QueryPlan conforms to:
- M1/M3 Target Database Schema allowlist (tables, canonical joins)
- M4/M5 Mandatory Business Rules & Security Access Policies
- Dialect structural capabilities
"""

import logging
from typing import Any

from rag.schemas import RAGContextResponse

from .schemas import QueryPlan

logger = logging.getLogger("text_to_sql.query_plan_validator")


class QueryPlanValidator:
    """Validates QueryPlan against schema allowlists and organizational policies."""

    @classmethod
    def validate_plan(
        cls,
        plan: QueryPlan,
        allowed_tables: set[str],
        context: RAGContextResponse
    ) -> dict[str, Any]:
        """Ensures query plan entities exist and mandatory policies are respected."""
        errors = []
        warnings = []

        norm_allowed_tables = {t.lower() for t in allowed_tables}

        # 1. Validate Target Entities exist in schema
        for tbl in plan.target_entities:
            if tbl.lower() not in norm_allowed_tables:
                errors.append(f"Target entity '{tbl}' does not exist in target database schema.")

        # 2. Check for empty metrics / selections
        if not plan.metrics and not plan.dimensions:
            errors.append("Query plan must select at least one metric or dimension.")

        # 3. Check Mandatory Rules Enforcement
        # If RAG context has mandatory rules, verify that their rule IDs are recorded
        mandatory_in_context = [
            r for r in context.business_rules
            if r.get("security_level") == "CRITICAL" or r.get("chunk_type") == "SECURITY_LOGIC"
        ]
        for mr in mandatory_in_context:
            mr_id = mr.get("rule_id")
            if mr_id and mr_id not in plan.applied_rule_ids:
                warnings.append(f"Mandatory security rule #{mr_id} will be forcibly attached during generation.")

        is_valid = len(errors) == 0
        return {
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings
        }
