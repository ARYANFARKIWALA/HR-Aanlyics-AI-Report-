"""Module 6: Text-to-SQL Engine Orchestrator Service.

Coordinates:
1. Context Retrieval (Module 5 RAG)
2. Ambiguity Detection & Clarification
3. Query Planning & Plan Validation
4. Dialect-Specific SQL Generation
5. Safety & Hallucination Defense
6. Plain-English Explanation & Knowledge Traceability
7. Strict Invariant: Never executes SQL (Execution is Module 8)
"""

import logging
from typing import Any

import sqlglot
from sqlalchemy.orm import Session
from sqlglot import exp

from backend.database.connection_manager import connection_manager
from rag.rag_service import RAGService

from .dialect import DialectTransformer
from .query_plan_validator import QueryPlanValidator
from .query_planner import QueryPlanner
from .safety import SQLSafetyValidator
from .schemas import (
    ReasoningMetadata,
    TextToSQLRequest,
    TextToSQLResponse,
)
from .sql_explainer import SQLExplainer
from .sql_generator import SQLGenerator
from .traceability import SQLTraceabilityMapper

logger = logging.getLogger("text_to_sql.service")

# In-memory history for session audit
_QUERY_GENERATION_HISTORY: list[dict[str, Any]] = []


class TextToSQLService:
    """Central AI Text-to-SQL Engine coordinator."""

    def __init__(self, db: Session):
        self.db = db
        self.rag_service = RAGService(db)
        self.traceability_mapper = SQLTraceabilityMapper(db)

    def generate_sql(self, request: TextToSQLRequest) -> TextToSQLResponse:
        """Translates natural language to verified, dialect-specific SQL."""
        db_id = request.database_id or "sqlite_hr_default"

        # Resolve dialect
        if request.target_dialect:
            dialect = request.target_dialect
        else:
            try:
                dialect = connection_manager.get_dialect_rules(db_id).dialect
            except Exception:
                dialect = "sqlite"

        # 1. Retrieve RAG Context (Module 5)
        context = self.rag_service.get_context_for_query(
            query=request.query,
            database_id=db_id,
            top_k=8
        )

        # Check for insufficient context
        if context.status == "INSUFFICIENT_CONTEXT":
            return TextToSQLResponse(
                status="INSUFFICIENT_CONTEXT",
                message=context.message or "No approved organizational knowledge sufficiently matches this query.",
                dialect=dialect,
                database_id=db_id,
                execution_permitted=False,
                confidence_score=0.0
            )

        # 2. Ambiguity Check
        ambiguity = QueryPlanner.detect_ambiguity(request.query, context)
        if ambiguity.is_ambiguous:
            status = "CLARIFICATION_REQUIRED" if ambiguity.ambiguity_type == "UNRESOLVED_SCHEMA_ENTITY" else "AMBIGUOUS_QUERY"
            return TextToSQLResponse(
                status=status,
                message=ambiguity.questions[0] if ambiguity.questions else "Your query contains ambiguous or underspecified criteria.",
                dialect=dialect,
                database_id=db_id,
                clarification=ambiguity,
                execution_permitted=False,
                confidence_score=0.4
            )

        # 3. Query Planning
        plan = QueryPlanner.plan_query(
            query=request.query,
            context=context,
            user_role=request.user_role,
            user_department=request.user_department,
            date_context=request.date_context
        )

        # 4. Schema Allowlist & Plan Validation
        try:
            schema_info = connection_manager.get_schema(db_id)
            if hasattr(schema_info, "table_allowlist") and schema_info.table_allowlist:
                allowed_tables = set(schema_info.table_allowlist)
                allowed_cols = schema_info.column_allowlist_map
            elif hasattr(schema_info, "tables"):
                if isinstance(schema_info.tables, dict):
                    allowed_tables = set(schema_info.tables.keys())
                    allowed_cols = {t: set(cols) for t, cols in schema_info.tables.items()}
                elif isinstance(schema_info.tables, list):
                    allowed_tables = {t.name for t in schema_info.tables}
                    allowed_cols = {t.name: {c.name for c in t.columns} for t in schema_info.tables}
                else:
                    allowed_tables = {"employees", "departments", "job_profiles", "compensation_history", "performance_reviews", "leave_records"}
                    allowed_cols = {t: set() for t in allowed_tables}
            else:
                allowed_tables = {"employees", "departments", "job_profiles", "compensation_history", "performance_reviews", "leave_records"}
                allowed_cols = {t: set() for t in allowed_tables}
        except Exception:
            allowed_tables = {"employees", "departments", "job_profiles", "compensation_history", "performance_reviews", "leave_records"}
            allowed_cols = {t: set() for t in allowed_tables}

        plan_val = QueryPlanValidator.validate_plan(
            plan=plan,
            allowed_tables=allowed_tables,
            context=context
        )
        if not plan_val["is_valid"]:
            return TextToSQLResponse(
                status="INVALID_PLAN",
                message="; ".join(plan_val["errors"]),
                dialect=dialect,
                database_id=db_id,
                warnings=plan_val["warnings"],
                execution_permitted=False,
                confidence_score=0.2
            )

        # 5. SQL Generation
        generated_sql = SQLGenerator.generate_sql(
            plan=plan,
            context=context,
            dialect=dialect,
            target_database_id=db_id
        )

        # 6. Safety & Mutation Defense
        safety = SQLSafetyValidator.validate_safety(generated_sql, dialect=dialect)
        if not safety["is_safe"]:
            return TextToSQLResponse(
                status="BLOCKED_BY_SAFETY",
                message=safety["reason"],
                sql=None,
                dialect=dialect,
                database_id=db_id,
                execution_permitted=False,
                confidence_score=0.0
            )

        # 7. Hallucination Detection
        hallucination = SQLSafetyValidator.detect_hallucinations(
            sql=generated_sql,
            allowed_tables=allowed_tables,
            allowed_columns=allowed_cols if any(allowed_cols.values()) else None,
            dialect=dialect
        )
        if hallucination["has_hallucinations"]:
            return TextToSQLResponse(
                status="BLOCKED_BY_SAFETY",
                message=hallucination["reason"],
                sql=generated_sql,
                dialect=dialect,
                database_id=db_id,
                execution_permitted=False,
                confidence_score=0.3
            )

        # 8. Traceability Mapping
        trace_meta = self.traceability_mapper.map_traceability(
            applied_rule_ids=plan.applied_rule_ids,
            reused_report_id=plan.reused_report_id
        )

        # 9. Plain-English Explanation
        explanation = None
        if request.include_explanation:
            explanation = SQLExplainer.explain_sql(
                sql=generated_sql,
                query_plan=plan.model_dump() if hasattr(plan, "model_dump") else plan.dict(),
                applied_rules=trace_meta.get("applied_rules", []),
                dialect=dialect
            )

        # 10. Extract tables & columns used via AST
        tables_used = []
        columns_used = []
        try:
            norm_diag = DialectTransformer.normalize_dialect_name(dialect)
            p_ast = sqlglot.parse_one(generated_sql, read=norm_diag)
            tables_used = sorted({t.name for t in p_ast.find_all(exp.Table)})
            columns_used = sorted({c.name for c in p_ast.find_all(exp.Column) if c.name not in ("*", "")})
        except Exception:
            pass

        reasoning_meta = ReasoningMetadata(
            intent_summary=plan.intent,
            target_dialect=dialect,
            entities_identified=plan.target_entities,
            metrics_identified=plan.metrics,
            dimensions_identified=plan.dimensions,
            filters_applied=plan.filters,
            applied_business_rules=[f"Rule ID #{r}" for r in plan.applied_rule_ids],
            confidence_score=0.95
        )

        response = TextToSQLResponse(
            status="SUCCESS",
            sql=generated_sql,
            dialect=dialect,
            database_id=db_id,
            explanation=explanation,
            query_plan=plan.model_dump() if hasattr(plan, "model_dump") else plan.dict() if request.include_plan else None,
            reasoning_metadata=reasoning_meta,
            applied_rules=trace_meta.get("applied_rules", []),
            reused_reports=trace_meta.get("reused_reports", []),
            tables_used=tables_used,
            columns_used=columns_used,
            warnings=plan_val.get("warnings", []),
            execution_permitted=False,  # Hard Invariant
            confidence_score=0.95
        )

        # Record in history
        _QUERY_GENERATION_HISTORY.append({
            "query": request.query,
            "database_id": db_id,
            "dialect": dialect,
            "status": response.status,
            "sql": response.sql,
            "confidence_score": response.confidence_score
        })

        return response

    def plan_only(self, request: TextToSQLRequest) -> dict[str, Any]:
        """Generates only the structured query plan without SQL generation."""
        db_id = request.database_id or "sqlite_hr_default"
        context = self.rag_service.get_context_for_query(query=request.query, database_id=db_id)
        plan = QueryPlanner.plan_query(
            query=request.query,
            context=context,
            user_role=request.user_role,
            user_department=request.user_department,
            date_context=request.date_context
        )
        return plan.model_dump() if hasattr(plan, "model_dump") else plan.dict()

    def explain_only(self, sql: str, dialect: str = "sqlite") -> str:
        """Explains any SQL query in plain English."""
        return SQLExplainer.explain_sql(sql=sql, dialect=dialect)

    @classmethod
    def get_history(cls) -> list[dict[str, Any]]:
        """Returns session query generation history."""
        return list(reversed(_QUERY_GENERATION_HISTORY[-50:]))
