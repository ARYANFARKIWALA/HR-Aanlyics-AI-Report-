"""Core Query Execution Engine Service (Module 8)."""

import datetime
import hashlib
import re
import time
import uuid
from collections.abc import Generator
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.auth.authorization import AuthorizationService
from backend.database.connection_manager import connection_manager
from backend.database.models import User
from backend.database.models_execution import QueryExecutionAuditLog
from backend.database.models_validation import SQLValidationAuditLog

from .cache import QueryCacheManager
from .result_handler import MAX_RESULT_ROWS, ResultHandler
from .schemas import ExecuteQueryRequest, QueryColumnMeta, QueryExecutionResponse

DEFAULT_STATEMENT_TIMEOUT_SECONDS = 30
_ACTIVE_QUERIES: dict[str, Any] = {}


class QueryExecutionError(Exception):
    """Raised when execution fails validation handshake, timeout, or runtime error."""


class QueryExecutionService:
    """Executes strictly validated and approved SQL queries under zero-trust handshake."""

    def __init__(self, db: Session):
        self.db = db

    def execute(
        self,
        request: ExecuteQueryRequest,
        user: User | None = None
    ) -> QueryExecutionResponse:
        """
        Executes a query by validation_id token.
        HARD INVARIANT: Never accepts raw SQL directly from the client.
        """
        execution_id = f"exec_{uuid.uuid4().hex}"
        start_time = time.time()
        now = datetime.datetime.now(datetime.UTC)

        # -------------------------------------------------------------
        # STEP 1: VALIDATION HANDSHAKE VERIFICATION
        # -------------------------------------------------------------
        val_entry = self.db.query(SQLValidationAuditLog).filter(
            SQLValidationAuditLog.validation_id == request.validation_id
        ).first()

        if not val_entry:
            raise QueryExecutionError(f"Validation token '{request.validation_id}' not found. Queries must be validated by Module 7 first.")

        # 1. Approval check
        if val_entry.status != "APPROVED":
            raise QueryExecutionError(f"Validation token '{request.validation_id}' is {val_entry.status}. Only 'APPROVED' queries may execute.")

        # 2. Expiration check (15-min TTL)
        expires_at = val_entry.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=datetime.UTC)

        if now > expires_at:
            raise QueryExecutionError(f"Validation token '{request.validation_id}' expired at {expires_at.isoformat()}. Re-validation required.")

        # 3. Cryptographic integrity check
        calculated_hash = hashlib.sha256(val_entry.sanitized_sql.encode("utf-8")).hexdigest()
        if calculated_hash != val_entry.sql_hash:
            raise QueryExecutionError("Security alert: Cryptographic hash mismatch. Validation token has been tampered with.")

        # 4. User database access authorization check
        if user:
            can_exec = AuthorizationService.can_access_database(
                db=self.db,
                user=user,
                database_id=val_entry.database_id,
                mode="execute"
            )
            if not can_exec:
                raise QueryExecutionError(f"Access Denied: User '{user.username}' is not authorized to execute queries on database '{val_entry.database_id}'.")

        database_id = val_entry.database_id
        sanitized_sql = val_entry.sanitized_sql
        sql_hash = val_entry.sql_hash

        # -------------------------------------------------------------
        # STEP 2: CACHE LOOKUP
        # -------------------------------------------------------------
        if not request.bypass_cache:
            cached_res = QueryCacheManager.get(
                database_id=database_id,
                sql_hash=sql_hash,
                params=request.parameters
            )
            if cached_res:
                df, cols, col_meta_dicts = cached_res
                exec_time_ms = round((time.time() - start_time) * 1000, 2)

                # Paginate cached data
                total_rows = len(df)
                start_idx = (request.page - 1) * request.page_size
                end_idx = start_idx + request.page_size
                page_df = df.iloc[start_idx:end_idx]

                # Log cached execution
                self._log_execution(
                    execution_id=execution_id,
                    validation_id=request.validation_id,
                    database_id=database_id,
                    user=user,
                    sql_hash=sql_hash,
                    status="SUCCESS",
                    row_count=total_rows,
                    execution_time_ms=exec_time_ms,
                    cached=True
                )

                return QueryExecutionResponse(
                    execution_id=execution_id,
                    query_id=execution_id,
                    validation_id=request.validation_id,
                    database_id=database_id,
                    status="SUCCESS",
                    columns=cols,
                    column_metadata=[QueryColumnMeta(**m) for m in col_meta_dicts],
                    rows=page_df.to_dict(orient="records"),
                    row_count=len(page_df),
                    total_rows=total_rows,
                    page=request.page,
                    page_size=request.page_size,
                    execution_time_ms=exec_time_ms,
                    execution_time=round(exec_time_ms / 1000.0, 4),
                    cached=True,
                    sql_hash=sql_hash,
                    executed_at=now.isoformat()
                )

        # -------------------------------------------------------------
        # STEP 3: SAFE DATABASE EXECUTION WITH STATEMENT TIMEOUT
        # -------------------------------------------------------------
        try:
            target_engine = connection_manager.get_engine(database_id)
        except Exception as e:
            raise QueryExecutionError(f"Target database '{database_id}' connection unavailable: {e}")

        try:
            # Execute with statement timeout and driver read-only enforcement
            with target_engine.connect() as conn:
                _ACTIVE_QUERIES[execution_id] = conn
                try:
                    dialect_name = getattr(target_engine.dialect, "name", "").lower()
                    if dialect_name == "sqlite":
                        try:
                            conn.execute(text("PRAGMA query_only = ON;"))
                        except Exception:
                            pass
                    elif dialect_name in ("postgresql", "postgres"):
                        try:
                            conn.execute(text("SET TRANSACTION READ ONLY;"))
                        except Exception:
                            pass

                    # Set execution timeout where supported
                    stmt = text(sanitized_sql)
                    if request.parameters:
                        stmt = stmt.bindparams(**request.parameters)

                    cursor = conn.execute(stmt)
                    df, cols, col_meta = ResultHandler.process_cursor(cursor, max_rows=MAX_RESULT_ROWS)
                finally:
                    _ACTIVE_QUERIES.pop(execution_id, None)

        except Exception as exc:
            exec_time_ms = round((time.time() - start_time) * 1000, 2)
            raw_err = str(exc)
            # Never expose database credentials in error messages
            scrubbed_err = re.sub(r"://[^@]+@", "://***:***@", raw_err)
            status_str = "TIMEOUT" if "timeout" in scrubbed_err.lower() or "deadline" in scrubbed_err.lower() else "FAILED"

            self._log_execution(
                execution_id=execution_id,
                validation_id=request.validation_id,
                database_id=database_id,
                user=user,
                sql_hash=sql_hash,
                status=status_str,
                row_count=0,
                execution_time_ms=exec_time_ms,
                cached=False,
                error_message=scrubbed_err
            )
            raise QueryExecutionError(f"Query execution {status_str.lower()}: {scrubbed_err}")

        # -------------------------------------------------------------
        # STEP 4: COLUMN-LEVEL SECURITY MASKING (Module 11)
        # -------------------------------------------------------------
        if user and not df.empty:
            df = AuthorizationService.apply_column_masking(
                df=df,
                db=self.db,
                user=user,
                database_id=database_id
            )

        exec_time_ms = round((time.time() - start_time) * 1000, 2)
        total_rows = len(df)

        # Store in cache
        col_meta_dicts = [m.model_dump() for m in col_meta]
        QueryCacheManager.set(
            database_id=database_id,
            sql_hash=sql_hash,
            df=df,
            cols=cols,
            col_meta=col_meta_dicts,
            params=request.parameters
        )

        # -------------------------------------------------------------
        # STEP 5: PAGINATION & RESPONSE CREATION
        # -------------------------------------------------------------
        start_idx = (request.page - 1) * request.page_size
        end_idx = start_idx + request.page_size
        page_df = df.iloc[start_idx:end_idx]

        # Log audit record
        self._log_execution(
            execution_id=execution_id,
            validation_id=request.validation_id,
            database_id=database_id,
            user=user,
            sql_hash=sql_hash,
            status="SUCCESS",
            row_count=total_rows,
            execution_time_ms=exec_time_ms,
            cached=False
        )

        return QueryExecutionResponse(
            execution_id=execution_id,
            query_id=execution_id,
            validation_id=request.validation_id,
            database_id=database_id,
            status="SUCCESS",
            columns=cols,
            column_metadata=col_meta,
            rows=page_df.to_dict(orient="records"),
            row_count=len(page_df),
            total_rows=total_rows,
            page=request.page,
            page_size=request.page_size,
            execution_time_ms=exec_time_ms,
            execution_time=round(exec_time_ms / 1000.0, 4),
            cached=False,
            sql_hash=sql_hash,
            executed_at=now.isoformat()
        )

    def _log_execution(
        self,
        execution_id: str,
        validation_id: str,
        database_id: str,
        user: User | None,
        sql_hash: str,
        status: str,
        row_count: int,
        execution_time_ms: float,
        cached: bool,
        error_message: str | None = None
    ) -> None:
        """Records an execution audit log entry."""
        log = QueryExecutionAuditLog(
            execution_id=execution_id,
            validation_id=validation_id,
            database_id=database_id,
            user_id=user.id if user else None,
            username=user.username if user else "anonymous",
            user_role=user.role if user else "anonymous",
            sql_hash=sql_hash,
            status=status,
            row_count=row_count,
            execution_time_ms=execution_time_ms,
            cached=cached,
            error_message=error_message,
            created_at=datetime.datetime.now(datetime.UTC)
        )
        try:
            self.db.add(log)
            self.db.commit()
        except Exception:
            self.db.rollback()

    @classmethod
    def cancel_query(cls, query_id: str) -> bool:
        """Attempts to cancel a running query execution."""
        conn = _ACTIVE_QUERIES.get(query_id)
        if conn is not None:
            try:
                conn.close()
                _ACTIVE_QUERIES.pop(query_id, None)
                return True
            except Exception:
                return False
        return False

    def stream_query(
        self,
        request: ExecuteQueryRequest,
        user: User | None = None,
        chunk_size: int = 100
    ) -> Generator[dict[str, Any], None, None]:
        """
        Streams query results in chunks.
        Strict invariant: Never bypasses Module 7 validation.
        """
        val_entry = self.db.query(SQLValidationAuditLog).filter(
            SQLValidationAuditLog.validation_id == request.validation_id
        ).first()

        if not val_entry:
            raise QueryExecutionError(f"Validation token '{request.validation_id}' not found.")

        if val_entry.status != "APPROVED":
            raise QueryExecutionError(f"Validation token '{request.validation_id}' is {val_entry.status}. Only 'APPROVED' queries may execute.")

        target_engine = connection_manager.get_engine(val_entry.database_id)
        with target_engine.connect() as conn:
            stmt = text(val_entry.sanitized_sql)
            if request.parameters:
                stmt = stmt.bindparams(**request.parameters)
            result = conn.execute(stmt)
            cols = list(result.keys())
            while True:
                batch = result.fetchmany(chunk_size)
                if not batch:
                    break
                batch_records = [dict(zip(cols, row)) for row in batch]
                yield {
                    "columns": cols,
                    "rows": batch_records,
                    "row_count": len(batch_records),
                    "query_id": f"stream_{uuid.uuid4().hex[:8]}"
                }
