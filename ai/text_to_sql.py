"""Text-to-SQL Engine with Enterprise SQL Repository Semantic Adaptation.

Transforms business natural language into validated SQL while preserving
historical enterprise business logic, joins, and effective-dating rules.
"""

import re
from typing import Any

from sqlalchemy.orm import Session

from rag.retrieval import rag_retriever
from sql.validator import SQLValidator

from .model import llm_client
from .prompts.explainer_prompts import SQL_EXPLAINER_PROMPT
from .prompts.system_prompts import TEXT_TO_SQL_SYSTEM_PROMPT


class TextToSQLService:
    """Intelligent reporting assistant converting questions into verified enterprise SQL."""

    @classmethod
    def generate_sql(
        cls,
        natural_query: str,
        db_session: Session,
        user_role: str = "admin",
        user_dept_id: int | None = None
    ) -> dict[str, Any]:
        """Translates natural language to SQL using semantic repository matching + LLM."""
        # 1. Check if RAG is initialized
        if not rag_retriever._initialized or not rag_retriever.sql_docs:
            rag_retriever.initialize(db_session)

        # 2. Semantic retrieval of existing verified SQL templates
        matched_templates = rag_retriever.search_sql_templates(natural_query, top_k=2)
        top_match = matched_templates[0] if matched_templates else None

        matched_template_title = top_match["title"] if (top_match and top_match.get("similarity_score", 0) > 0.15) else None
        reference_sql = top_match["raw_sql"] if matched_template_title else ""
        reference_rules = top_match.get("business_rules", "") if matched_template_title else ""

        # 3. Build prompt including enterprise template reference
        prompt = f"""USER QUESTION:
{natural_query}
"""
        if matched_template_title:
            prompt += f"""
RELEVANT VERIFIED ENTERPRISE SQL TEMPLATE FROM REPOSITORY:
Template Name: {matched_template_title}
Verified Business Rules: {reference_rules}
Existing SQL:
{reference_sql}

INSTRUCTIONS:
You may adapt or reuse this verified enterprise query for the user's question, preserving its join conditions and effective-dating logic.
Return ONLY valid read-only SQL.
"""
        else:
            prompt += "\nGenerate the most accurate read-only SQL query for this question using the provided schema.\n"

        # 4. Generate SQL from LLM
        response_text = llm_client.generate(prompt, system_instruction=TEXT_TO_SQL_SYSTEM_PROMPT)

        # Extract SQL from markdown or code blocks
        sql_candidate = cls._extract_sql(response_text)

        # If in offline mode or LLM returned fallback placeholder, use the verified enterprise template
        if (not sql_candidate or "SELECT" not in sql_candidate.upper() or "fallback" in response_text.lower() or "offline" in response_text.lower()) and top_match:
            sql_candidate = top_match["raw_sql"]
            matched_template_title = top_match["title"]

        # 5. Apply Row-Level Security filters if required
        filtered_sql = SQLValidator.apply_security_filter(sql_candidate, user_role, user_dept_id)

        # 6. Validate generated SQL against safety guardrails
        is_valid, validation_msg, analysis = SQLValidator.validate(
            filtered_sql,
            user_role=user_role,
            user_dept_id=user_dept_id
        )

        if not is_valid and top_match:
            # If invalid and we had a template, fall back safely
            filtered_sql = top_match["raw_sql"]
            is_valid, validation_msg, analysis = SQLValidator.validate(filtered_sql, user_role, user_dept_id)

        # 7. Generate Plain-English explanation for business users
        explanation = cls.explain_sql(filtered_sql, analysis.to_dict())

        return {
            "natural_query": natural_query,
            "sql": filtered_sql,
            "is_valid": is_valid,
            "validation_message": validation_msg,
            "analysis": analysis.to_dict(),
            "matched_template": matched_template_title,
            "similarity_score": top_match["similarity_score"] if top_match else 0.0,
            "explanation": explanation
        }

    @classmethod
    def explain_sql(cls, sql_text: str, analysis_dict: dict[str, Any]) -> str:
        """Explains query semantics, joins, and filters in plain English for business users."""
        prompt = f"""Please explain this SQL query for an executive HR business audience:

SQL QUERY:
{sql_text}

QUERY METADATA:
- Tables Joined: {', '.join(analysis_dict.get('tables', []))}
- Joins: {analysis_dict.get('joins', [])}
- Effective Dating Filters Applied: {analysis_dict.get('has_effective_dating', False)} ({analysis_dict.get('effective_dating_clauses', [])})
- Where Conditions: {analysis_dict.get('where_conditions', [])}
"""
        return llm_client.generate(prompt, system_instruction=SQL_EXPLAINER_PROMPT)

    @classmethod
    def _extract_sql(cls, text: str) -> str:
        """Extracts SQL code block or raw query from text."""
        # Try finding ```sql ... ```
        match = re.search(r"```(?:sql)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # If text begins with SELECT or WITH
        text_clean = text.strip()
        if text_clean.upper().startswith("SELECT") or text_clean.upper().startswith("WITH"):
            return text_clean

        # Search for first SELECT or WITH
        select_idx = text_clean.upper().find("SELECT")
        if select_idx != -1:
            return text_clean[select_idx:].strip()

        return text_clean
