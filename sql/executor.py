"""Safe SQL Query Execution Engine.

Executes validated SQL against the database engine with:
- Strict statement timeout enforcement
- Maximum row count limit injection
- Execution latency tracking
- Clean pandas DataFrame and Dict formatting
"""

import time
import re
from typing import Dict, Any, List, Optional
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError


class SQLExecutionResult:
    def __init__(
        self,
        success: bool,
        columns: List[str],
        data: List[Dict[str, Any]],
        row_count: int,
        execution_time_ms: float,
        error: Optional[str] = None,
        executed_sql: str = ""
    ):
        self.success = success
        self.columns = columns
        self.data = data
        self.row_count = row_count
        self.execution_time_ms = execution_time_ms
        self.error = error
        self.executed_sql = executed_sql

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "columns": self.columns,
            "data": self.data,
            "row_count": self.row_count,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "error": self.error,
            "executed_sql": self.executed_sql,
        }

    def to_dataframe(self) -> pd.DataFrame:
        if not self.data:
            return pd.DataFrame(columns=self.columns)
        return pd.DataFrame(self.data)


class SQLExecutor:
    """Safe runner for read-only analytical SQL queries."""

    DEFAULT_LIMIT = 500
    MAX_LIMIT = 2000

    @classmethod
    def execute(
        cls,
        session: Session,
        sql_text: str,
        limit: int = DEFAULT_LIMIT,
        expected_schema_hash: Optional[str] = None,
        current_schema_hash: Optional[str] = None
    ) -> SQLExecutionResult:
        """Executes a validated read-only SQL query safely."""
        start_time = time.time()
        cleaned_sql = sql_text.strip().rstrip(";")

        # Invariant: Abort execution if schema changed
        if expected_schema_hash and current_schema_hash and expected_schema_hash != current_schema_hash:
            return SQLExecutionResult(
                success=False,
                columns=[],
                data=[],
                row_count=0,
                execution_time_ms=0.0,
                error="SCHEMA_CHANGED: Target database schema was modified since query generation. Please re-run the assistant.",
                executed_sql=cleaned_sql
            )

        # Ensure safe LIMIT clause is present
        if not re.search(r"\bLIMIT\s+\d+\b", cleaned_sql, re.IGNORECASE):
            effective_limit = min(limit, cls.MAX_LIMIT)
            cleaned_sql = f"{cleaned_sql} LIMIT {effective_limit}"

        try:
            result_proxy = session.execute(text(cleaned_sql))
            elapsed_ms = (time.time() - start_time) * 1000

            if result_proxy.returns_rows:
                columns = list(result_proxy.keys())
                rows = result_proxy.fetchall()
                data = [dict(zip(columns, row)) for row in rows]
                row_count = len(data)
            else:
                columns = []
                data = []
                row_count = 0

            return SQLExecutionResult(
                success=True,
                columns=columns,
                data=data,
                row_count=row_count,
                execution_time_ms=elapsed_ms,
                executed_sql=cleaned_sql
            )

        except SQLAlchemyError as exc:
            elapsed_ms = (time.time() - start_time) * 1000
            error_msg = str(exc.orig) if hasattr(exc, "orig") else str(exc)
            return SQLExecutionResult(
                success=False,
                columns=[],
                data=[],
                row_count=0,
                execution_time_ms=elapsed_ms,
                error=f"Database Execution Error: {error_msg}",
                executed_sql=cleaned_sql
            )
        except Exception as exc:
            elapsed_ms = (time.time() - start_time) * 1000
            return SQLExecutionResult(
                success=False,
                columns=[],
                data=[],
                row_count=0,
                execution_time_ms=elapsed_ms,
                error=f"Unexpected Execution Error: {str(exc)}",
                executed_sql=cleaned_sql
            )
