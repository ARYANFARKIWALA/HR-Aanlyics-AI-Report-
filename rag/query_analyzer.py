"""Module 5: Query Understanding & Analyzer.

Analyzes natural language questions to extract:
- Domain entities (Employee, Department, Job, Compensation, Leave)
- Quantitative metrics (Salary, Headcount, Days, Rating)
- Temporal concepts (Current, Today, 2026, Historical)
- Target table candidate candidates
Does NOT generate SQL.
"""

import re
from typing import Any, ClassVar


class QueryAnalyzer:
    """Extracts semantic intents, entities, and keywords from natural language reporting queries."""

    ENTITY_MAP: ClassVar[dict[str, list[str]]] = {
        "employee": ["employee", "staff", "worker", "headcount", "person", "team member"],
        "department": ["department", "dept", "division", "cost center", "business unit"],
        "attrition": ["attrition", "turnover", "separation", "resignation", "terminated", "exits", "exit"],
        "compensation": ["salary", "compensation", "pay", "bonus", "compa", "wage", "remuneration"],
        "performance": ["performance", "rating", "review", "appraisal", "goal", "score"],
        "leave": ["leave", "absence", "pto", "vacation", "sick day", "time off"],
        "job": ["job", "role", "title", "position", "profile", "designation"]
    }

    METRIC_MAP: ClassVar[dict[str, list[str]]] = {
        "attrition": ["attrition", "turnover", "separation", "resignation", "exit rate", "turnover rate", "churn"],
        "salary": ["salary", "base salary", "compensation", "pay", "wage"],
        "bonus": ["bonus", "incentive"],
        "headcount": ["count", "number of", "headcount", "how many", "total employees"],
        "rating": ["rating", "performance rating", "score", "appraisal score"],
        "days_taken": ["days", "leave days", "absence days", "time off"]
    }

    TABLE_HINTS: ClassVar[dict[str, str]] = {
        "employee": "employees",
        "department": "departments",
        "attrition": "employees",
        "compensation": "compensation_history",
        "performance": "performance_reviews",
        "leave": "leave_records",
        "job": "job_profiles"
    }


    @classmethod
    def analyze(cls, query: str) -> dict[str, Any]:
        """Analyzes question and returns extracted entities, metrics, temporal scope, and candidate tables."""
        q_clean = query.lower()

        entities = []
        candidate_tables = []
        for entity, keywords in cls.ENTITY_MAP.items():
            if any(kw in q_clean for kw in keywords):
                entities.append(entity)
                candidate_tables.append(cls.TABLE_HINTS[entity])

        metrics = []
        for metric, keywords in cls.METRIC_MAP.items():
            if any(kw in q_clean for kw in keywords):
                metrics.append(metric)

        # Temporal analysis
        is_current = any(w in q_clean for w in ["current", "currently", "active", "present", "now", "today"])
        has_historical = any(w in q_clean for w in ["history", "historical", "over time", "trend", "past", "previous"])

        time_frame = "CURRENT" if is_current else ("HISTORICAL" if has_historical else "ALL")

        # Department filter extracted
        dept_match = re.search(r"in (?:the )?([a-z\s]+) department", q_clean)
        department_filter = dept_match.group(1).strip() if dept_match else None

        return {
            "query": query,
            "entities": entities,
            "metrics": metrics,
            "temporal_scope": time_frame,
            "candidate_tables": list(dict.fromkeys(candidate_tables)),
            "department_filter": department_filter
        }
