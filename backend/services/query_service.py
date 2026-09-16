"""Query Service orchestrating Text-to-SQL, Validation, Execution, Masking, and Auditing."""

import time
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from ..database.models import User
from ai.text_to_sql import TextToSQLService
from sql.validator import SQLValidator
from sql.executor import SQLExecutor
from security.permissions import mask_pii_dataframe
from security.audit import AuditLogger


class QueryService:
    """Orchestrates natural language processing to secured SQL execution."""

    @classmethod
    def process_natural_query(
        cls,
        natural_query: str,
        user: User,
        session: Session
    ) -> Dict[str, Any]:
        start_time = time.time()

        # 1. Generate SQL using RAG + AI
        gen_result = TextToSQLService.generate_sql(
            natural_query=natural_query,
            db_session=session,
            user_role=user.role,
            user_dept_id=user.department_id
        )

        sql_to_run = gen_result["sql"]
        is_valid = gen_result["is_valid"]
        validation_msg = gen_result["validation_message"]
        analysis = gen_result["analysis"]
        matched_template = gen_result.get("matched_template")
        explanation = gen_result.get("explanation", "")

        # 2. If validation failed, log rejection and return
        if not is_valid:
            elapsed_ms = (time.time() - start_time) * 1000
            AuditLogger.log_query(
                session=session,
                username=user.username,
                user_role=user.role,
                natural_query=natural_query,
                generated_sql=sql_to_run,
                execution_time_ms=elapsed_ms,
                row_count=0,
                status="REJECTED",
                error_details=validation_msg,
                user_id=user.id
            )
            return {
                "success": False,
                "natural_query": natural_query,
                "sql": sql_to_run,
                "error": f"Validation Guardrail Violation: {validation_msg}",
                "matched_template": matched_template,
                "explanation": explanation,
                "data": [],
                "columns": [],
                "row_count": 0,
                "execution_time_ms": round(elapsed_ms, 2)
            }

        # 3. Execute safe query
        exec_result = SQLExecutor.execute(session, sql_to_run)

        # 4. Handle execution error
        if not exec_result.success:
            elapsed_ms = (time.time() - start_time) * 1000
            AuditLogger.log_query(
                session=session,
                username=user.username,
                user_role=user.role,
                natural_query=natural_query,
                generated_sql=sql_to_run,
                execution_time_ms=elapsed_ms,
                row_count=0,
                status="FAILED",
                error_details=exec_result.error,
                user_id=user.id
            )
            return {
                "success": False,
                "natural_query": natural_query,
                "sql": sql_to_run,
                "error": exec_result.error,
                "matched_template": matched_template,
                "explanation": explanation,
                "data": [],
                "columns": [],
                "row_count": 0,
                "execution_time_ms": round(elapsed_ms, 2)
            }

        # 5. Apply PII Masking based on user role
        df = exec_result.to_dataframe()
        masked_df = mask_pii_dataframe(df, user.role)
        final_data = masked_df.to_dict(orient="records")

        elapsed_ms = (time.time() - start_time) * 1000

        # 6. Audit Log Success
        AuditLogger.log_query(
            session=session,
            username=user.username,
            user_role=user.role,
            natural_query=natural_query,
            generated_sql=exec_result.executed_sql,
            execution_time_ms=elapsed_ms,
            row_count=exec_result.row_count,
            status="SUCCESS",
            user_id=user.id
        )

        return {
            "success": True,
            "natural_query": natural_query,
            "sql": exec_result.executed_sql,
            "matched_template": matched_template,
            "explanation": explanation,
            "columns": exec_result.columns,
            "data": final_data,
            "row_count": exec_result.row_count,
            "execution_time_ms": round(elapsed_ms, 2),
            "analysis": analysis
        }
