"""FastAPI Routes for Module 8 - Query Execution Engine."""

import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.models import User
from backend.database.models_execution import QueryExecutionAuditLog
from backend.database.connection_manager import connection_manager
from backend.auth.dependencies import get_current_user, require_permission
from query_execution.schemas import (
    ExecuteQueryRequest,
    QueryExecutionResponse,
)
from query_execution.service import QueryExecutionService, QueryExecutionError
from query_execution.cache import QueryCacheManager

router = APIRouter(prefix="/api/query-execution", tags=["Query Execution Engine"])


@router.post("/execute", response_model=QueryExecutionResponse)
def execute_query(
    request: ExecuteQueryRequest,
    current_user: User = Depends(require_permission("sql:execute")),
    db: Session = Depends(get_db)
):
    """
    Executes a query by validation_id token.
    Enforces validation handshake, cryptographic hash match, timeout, row limits, and CLS data masking.
    HARD INVARIANT: Accepts NO raw SQL from clients.
    """
    service = QueryExecutionService(db=db)
    try:
        response = service.execute(request=request, user=current_user)
        return response
    except QueryExecutionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution error: {str(e)}"
        )


@router.get("/history")
def get_execution_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns query execution audit trail."""
    query = db.query(QueryExecutionAuditLog)
    if current_user.role != "admin":
        query = query.filter(QueryExecutionAuditLog.user_id == current_user.id)

    logs = query.order_by(QueryExecutionAuditLog.created_at.desc()).limit(limit).all()
    results = []
    for l in logs:
        results.append({
            "execution_id": l.execution_id,
            "validation_id": l.validation_id,
            "database_id": l.database_id,
            "username": l.username,
            "status": l.status,
            "row_count": l.row_count,
            "execution_time_ms": l.execution_time_ms,
            "cached": l.cached,
            "error_message": l.error_message,
            "created_at": l.created_at.isoformat() if l.created_at else None
        })
    return {"executions": results}


@router.post("/cache/clear")
def clear_cache(current_user: User = Depends(require_permission("sql:execute"))):
    """Clears in-memory query result cache."""
    QueryCacheManager.clear()
    return {"message": "Query cache cleared successfully."}


@router.get("/health")
def get_execution_health(current_user: User = Depends(get_current_user)):
    """Checks reachability of registered execution database targets."""
    registered = connection_manager.list_databases_safe()
    health_results = []
    for d in registered:
        db_id = d["database_id"]
        try:
            eng = connection_manager.get_engine(db_id)
            with eng.connect() as conn:
                conn.execute(connection_manager.get_dialect_rules(db_id).dummy_table_clause if hasattr(connection_manager.get_dialect_rules(db_id), "dummy_table_clause") else "SELECT 1")
            health_results.append({"database_id": db_id, "status": "HEALTHY"})
        except Exception as e:
            health_results.append({"database_id": db_id, "status": "UNHEALTHY", "error": str(e)})

    return {"databases": health_results}
