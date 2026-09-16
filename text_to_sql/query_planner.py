"""Module 6: Query Planner & Ambiguity Detector.

Formulates structured reporting query plans from natural language requests and
retrieved RAG context:
- Identifies business intent, target entities, metrics, dimensions, and group-by clauses.
- Detects ambiguous or underspecified requests.
- Incorporates mandatory rules and effective-dating policies into the plan.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from .schemas import QueryPlan, ClarificationRequest
from rag.schemas import RAGContextResponse

logger = logging.getLogger("text_to_sql.query_planner")

METRIC_PATTERNS = [
    (r"\b(headcount|count of employees|number of employees|employee count|staff count)\b", "COUNT(employees.id)", "headcount"),
    (r"\b(average salary|avg salary|mean salary|mean compensation)\b", "ROUND(AVG(compensation_history.base_salary), 2)", "average_salary"),
    (r"\b(total salary|sum of salary|total payroll|payroll expense)\b", "SUM(compensation_history.base_salary)", "total_payroll"),
    (r"\b(max salary|maximum salary|highest salary)\b", "MAX(compensation_history.base_salary)", "highest_salary"),
    (r"\b(min salary|minimum salary|lowest salary)\b", "MIN(compensation_history.base_salary)", "lowest_salary"),
    (r"\b(attrition rate|turnover rate)\b", "ROUND(CAST(COUNT(CASE WHEN employees.status = 'Terminated' THEN 1 END) AS FLOAT) / COUNT(*) * 100, 2)", "attrition_rate"),
    (r"\b(monthly employee attrition|employee attrition|attrition count|attrition|terminations|turnover count)\b", "COUNT(employees.id)", "attrition_count"),
]

DIMENSION_PATTERNS = [
    (r"\b(by department|per department|each department|department-wise|grouped by department)\b", "departments.name", "department"),
    (r"\b(by job title|by position|per role|by title|per title)\b", "job_profiles.title", "job_title"),
    (r"\b(by gender|per gender)\b", "employees.gender", "gender"),
    (r"\b(by location|per location|by office)\b", "departments.location", "location"),
    (r"\b(monthly|by month|per month|each month|month-wise)\b", "strftime('%Y-%m', employees.termination_date)", "month"),
]


class QueryPlanner:
    """Builds structured query execution plans before SQL generation."""

    @classmethod
    def detect_ambiguity(cls, query: str, context: RAGContextResponse) -> ClarificationRequest:
        """Detects if query is underspecified or ambiguous."""
        q_lower = query.lower().strip()
        questions = []
        suggestions = []

        # 0. Anti-hallucination / Unresolved schema entities check
        unresolved_keywords = ["crypto", "bitcoin", "weather", "shoe", "flight", "inventory", "stock_price", "401k_match_rate"]
        for kw in unresolved_keywords:
            if kw in q_lower:
                questions.append(f"The concept '{kw}' is not available in the HR schema or knowledge base. Did you mean to query employees, departments, or compensation?")
                suggestions.append("Show employee headcount by department")
                suggestions.append("Show employee attrition by department")
                return ClarificationRequest(
                    is_ambiguous=True,
                    ambiguity_type="UNRESOLVED_SCHEMA_ENTITY",
                    questions=questions,
                    suggested_queries=suggestions
                )

        # 1. Ambiguous metric without definition
        if "turnover" in q_lower and "rate" not in q_lower and "count" not in q_lower and "monthly" not in q_lower and "attrition" not in q_lower:
            questions.append("Do you want the voluntary turnover count or the percentage turnover rate?")
            suggestions.append("Show employee turnover rate by department")
            suggestions.append("Show count of employee resignations this year")

        # 2. Ambiguous temporal context
        if any(w in q_lower for w in ["history", "trend", "over time", "past", "last few years"]) and not re.search(r"\b(20\d\d|last \d+ (months|years)|quarter)\b", q_lower):
            questions.append("Which time period would you like to analyze (e.g. 2025, 2026, or trailing 12 months)?")
            suggestions.append(f"{query} for year 2025")
            suggestions.append(f"{query} trailing 12 months")

        # 3. Completely vague prompt
        tokens = [w for w in q_lower.split() if len(w) > 2]
        if len(tokens) <= 2 and not any(k in q_lower for k in ["employee", "salary", "headcount", "department", "attrition"]):
            questions.append("Could you specify the HR domain or metric you are looking for (e.g. headcount, salary, or department)?")
            suggestions.append("Show active headcount by department")
            suggestions.append("Show average salary by department")

        is_ambiguous = len(questions) > 0
        return ClarificationRequest(
            is_ambiguous=is_ambiguous,
            ambiguity_type="AMBIGUOUS_SPECIFICATION" if is_ambiguous else None,
            questions=questions,
            suggested_queries=suggestions
        )

    @classmethod
    def plan_query(
        cls,
        query: str,
        context: RAGContextResponse,
        user_role: str = "admin",
        user_department: Optional[str] = None,
        date_context: Optional[str] = None
    ) -> QueryPlan:
        """Formulates QueryPlan incorporating RAG retrieved rules and schema knowledge."""
        q_lower = query.lower().strip()
        is_attrition_query = "attrition" in q_lower or "turnover" in q_lower or "termination" in q_lower

        # 1. Identify Metrics & Aggregations
        metrics = []
        for pat, expr, name in METRIC_PATTERNS:
            if re.search(pat, q_lower):
                metrics.append(f"{expr} AS {name}")

        # Default metric if none found
        if not metrics:
            if "list" in q_lower or "show" in q_lower or "all" in q_lower:
                metrics = ["employees.id", "employees.first_name", "employees.last_name", "employees.status"]
            else:
                metrics = ["COUNT(*) AS total_count"]

        # 2. Identify Dimensions & Group By
        dimensions = []
        group_by = []
        for pat, col, name in DIMENSION_PATTERNS:
            if re.search(pat, q_lower):
                # Adjust temporal dimension if not attrition query
                actual_col = col
                if name == "month" and not is_attrition_query:
                    actual_col = "strftime('%Y-%m', employees.hire_date)"
                dimensions.append(actual_col)
                group_by.append(actual_col)

        # 3. Determine Target Entities & Joins
        target_entities = ["employees"]
        joins = []

        if any("department" in d or "departments" in d for d in dimensions + metrics) or "department" in q_lower:
            target_entities.append("departments")
            joins.append("INNER JOIN departments ON employees.department_id = departments.id")

        if any("compensation_history" in d for d in dimensions + metrics) or any("base_salary" in m for m in metrics):
            target_entities.append("compensation_history")
            joins.append("INNER JOIN compensation_history ON employees.id = compensation_history.employee_id")

        if any("job_profiles" in d for d in dimensions + metrics) or "job_title" in q_lower:
            target_entities.append("job_profiles")
            joins.append("INNER JOIN job_profiles ON employees.job_profile_id = job_profiles.id")

        # 4. Mandatory Business Rules & Filters from RAG context
        filters = []
        applied_rule_ids = []

        # Active vs Attrition employee filter
        if not is_attrition_query:
            filters.append("employees.status = 'ACTIVE'")
        else:
            filters.append("employees.status = 'Terminated'")

        # Temporal filter for year
        year_match = re.search(r"\b(20\d\d)\b", q_lower)
        if year_match:
            yr = year_match.group(1)
            if is_attrition_query:
                filters.append(f"employees.termination_date >= '{yr}-01-01'")
                filters.append(f"employees.termination_date <= '{yr}-12-31'")
            else:
                filters.append(f"employees.hire_date >= '{yr}-01-01'")
                filters.append(f"employees.hire_date <= '{yr}-12-31'")

        # Incorporate approved rules from context
        for rule in context.business_rules:
            r_id = rule.get("rule_id")
            if r_id and r_id not in applied_rule_ids:
                applied_rule_ids.append(r_id)

        # 5. Security & Row-Level Access Policies
        if user_role.upper() != "ADMIN" and user_department:
            filters.append(f"departments.name = '{user_department}'")

        # 6. Effective Dating Strategy
        effective_strategy = "CURRENT_ACTIVE" if not is_attrition_query else None
        if date_context and date_context != "current":
            effective_strategy = "HISTORICAL_AS_OF"

        # 7. Check if existing report pattern reused
        reused_rpt_id = None
        if context.existing_reports:
            first_rpt = context.existing_reports[0]
            reused_rpt_id = first_rpt.get("report_id")

        # 8. Order By & Limit
        order_by = []
        limit = None
        if "top" in q_lower:
            top_match = re.search(r"\btop\s+(\d+)\b", q_lower)
            limit = int(top_match.group(1)) if top_match else 10
            if metrics:
                first_alias = metrics[0].split(" AS ")[-1] if " AS " in metrics[0] else metrics[0]
                order_by.append(f"{first_alias} DESC")
        elif group_by:
            for g in group_by:
                order_by.append(f"{g} ASC")

        return QueryPlan(
            intent=f"Report request: {query}",
            target_entities=target_entities,
            metrics=metrics,
            dimensions=dimensions,
            group_by=group_by,
            order_by=order_by,
            filters=filters,
            joins=joins,
            effective_date_strategy=effective_strategy,
            applied_rule_ids=applied_rule_ids,
            reused_report_id=reused_rpt_id,
            limit=limit
        )
