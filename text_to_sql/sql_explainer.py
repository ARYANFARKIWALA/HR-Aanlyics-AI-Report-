"""Module 6: SQL Plain-English Explainer.

Translates complex SQL queries, joins, and filters into clear,
jargon-free business explanations for HR stakeholders.
"""

import logging
from typing import Any

import sqlglot
from sqlglot import exp

logger = logging.getLogger("text_to_sql.sql_explainer")


class SQLExplainer:
    """Provides plain English translations of generated SQL queries."""

    @classmethod
    def explain_sql(
        cls,
        sql: str,
        query_plan: dict[str, Any] | None = None,
        applied_rules: list[dict[str, Any]] | None = None,
        dialect: str = "sqlite"
    ) -> str:
        """Constructs an intuitive plain-English explanation of the SQL statement."""
        sections = []

        try:
            parsed = sqlglot.parse_one(sql)
        except Exception:
            parsed = None

        # 1. Summary / Purpose
        if query_plan and query_plan.get("intent"):
            sections.append(f"**Report Objective:** {query_plan['intent'].replace('Report request: ', '')}")

        # 2. Selected Metrics & Dimensions
        if parsed:
            [s.sql() for s in parsed.find_all(exp.Select)]
            tables = [t.name for t in parsed.find_all(exp.Table)]
            unique_tables = sorted(set(tables))

            sections.append(f"**Data Sources:** Retrieves data from `{', '.join(unique_tables)}`.")

            # Joins explanation
            joins = list(parsed.find_all(exp.Join))
            if joins:
                join_desc = []
                for j in joins:
                    join_desc.append(f"- Joined `{j.this.sql()}` on `{j.args.get('on')}`")
                sections.append("**Table Relationships:**\n" + "\n".join(join_desc))

            # Filters explanation
            where = parsed.find(exp.Where)
            if where:
                sections.append(f"**Filters Applied:**\n- Condition: `{where.this.sql()}`")

            # Group By
            group = parsed.find(exp.Group)
            if group:
                sections.append(f"**Aggregation:** Grouped by `{group.sql().replace('GROUP BY ', '')}`.")

            # Order By
            order = parsed.find(exp.Order)
            if order:
                sections.append(f"**Sorting:** Ordered by `{order.sql().replace('ORDER BY ', '')}`.")

        # 3. Applied Organizational Rules
        if applied_rules:
            rule_lines = []
            for r in applied_rules:
                rule_lines.append(f"- **{r.get('rule_code', 'RULE')}**: {r.get('rule_name', '')} — *{r.get('natural_language_rule', '')}*")
            sections.append("**Applied Organizational Rules & Policies:**\n" + "\n".join(rule_lines))

        # 4. Dialect & Engine Note
        sections.append(f"**Dialect Target:** Optimized specifically for `{dialect.upper()}` SQL engine.")

        return "\n\n".join(sections)
