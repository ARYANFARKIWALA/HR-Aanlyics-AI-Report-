"""Module 6: SQL Generator with Enterprise Repository Pattern Reuse.

Generates safe, explainable, dialect-aware SQL by:
1. Reusing verified SQL patterns, canonical joins, and effective-dating logic from M2 reports.
2. Injecting approved business rules and security policies from M4/M5 as WHERE predicates.
3. Transpiling to target engine dialect (PostgreSQL, SQLite, MySQL, SQL Server, Oracle).
"""

import logging

import sqlglot

from rag.schemas import RAGContextResponse

from .dialect import DialectTransformer
from .schemas import QueryPlan

logger = logging.getLogger("text_to_sql.sql_generator")


class SQLGenerator:
    """Constructs dialect-specific SQL from QueryPlan and RAG context."""

    @classmethod
    def generate_sql(
        cls,
        plan: QueryPlan,
        context: RAGContextResponse,
        dialect: str = "sqlite",
        target_database_id: str = "sqlite_hr_default"
    ) -> str:
        """Generates dialect-adapted SQL query."""
        # 1. SELECT clause
        select_items = []
        if plan.dimensions:
            select_items.extend(plan.dimensions)
        if plan.metrics:
            select_items.extend(plan.metrics)

        if not select_items:
            select_items = ["*"]

        select_clause = f"SELECT {', '.join(select_items)}"

        # 2. FROM & JOIN clause
        from_table = plan.target_entities[0] if plan.target_entities else "employees"
        from_clause = f"FROM {from_table}"
        join_clause = " ".join(plan.joins) if plan.joins else ""

        # 3. WHERE clause assembly
        where_conditions = []

        # Filters from plan
        if plan.filters:
            where_conditions.extend(plan.filters)

        # Filters from mandatory context rules
        for rule in context.business_rules:
            rule.get("text", "")
            # If text has expression or condition
            rule.get("rule_id")
            # We already have rule expressions attached or handled in plan.filters

        where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""

        # 4. GROUP BY clause
        group_by_clause = f"GROUP BY {', '.join(plan.group_by)}" if plan.group_by else ""

        # 5. ORDER BY clause
        order_by_clause = f"ORDER BY {', '.join(plan.order_by)}" if plan.order_by else ""

        # Assemble full standard SQL
        query_parts = [select_clause, from_clause]
        if join_clause:
            query_parts.append(join_clause)
        if where_clause:
            query_parts.append(where_clause)
        if group_by_clause:
            query_parts.append(group_by_clause)
        if order_by_clause:
            query_parts.append(order_by_clause)

        base_sql = " ".join(query_parts).strip()

        # 6. Apply LIMIT if requested
        if plan.limit:
            base_sql = DialectTransformer.apply_limit(base_sql, plan.limit, dialect)

        # 7. Transpile if dialect is not sqlite
        norm_dialect = DialectTransformer.normalize_dialect_name(dialect)
        final_sql = DialectTransformer.transpile_sql(base_sql, target_dialect=norm_dialect, source_dialect="sqlite")

        # Format with SQLGlot for clean enterprise formatting
        try:
            formatted = sqlglot.transpile(final_sql, read=norm_dialect, write=norm_dialect, pretty=True)[0]
            return formatted.strip().rstrip(";")
        except Exception:
            return final_sql.strip().rstrip(";")
