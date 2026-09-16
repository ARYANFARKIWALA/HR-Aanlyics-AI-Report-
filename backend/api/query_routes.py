"""Natural language and SQL query API routes."""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database.connection import get_db
from ..database.models import User
from ..auth.dependencies import get_current_user
from ..services.query_service import QueryService
from sql.validator import SQLValidator
from sql.executor import SQLExecutor
from sql.parser import SQLParser
from ai.text_to_sql import TextToSQLService

router = APIRouter(prefix="/api/query", tags=["Query Assistant"])


class NaturalQueryRequest(BaseModel):
    query: str


class SQLExplainRequest(BaseModel):
    sql: str


class DirectSQLExecuteRequest(BaseModel):
    sql: str
    limit: Optional[int] = 500


@router.post("/ask")
def ask_natural_language_query(
    req: NaturalQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Translates natural language question into validated SQL and executes it."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty")

    result = QueryService.process_natural_query(
        natural_query=req.query,
        user=current_user,
        session=db
    )
    return result


@router.post("/explain")
def explain_sql_query(
    req: SQLExplainRequest,
    current_user: User = Depends(get_current_user)
):
    """Explains a complex SQL query in plain English for business users."""
    if not req.sql.strip():
        raise HTTPException(status_code=400, detail="SQL query cannot be empty")

    analysis = SQLParser.parse_query(req.sql)
    explanation = TextToSQLService.explain_sql(req.sql, analysis.to_dict())

    return {
        "sql": req.sql,
        "analysis": analysis.to_dict(),
        "explanation": explanation
    }


@router.post("/execute-direct")
def execute_direct_sql(
    req: DirectSQLExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Executes a direct SQL query after strict guardrail validation."""
    is_valid, msg, analysis = SQLValidator.validate(
        req.sql,
        user_role=current_user.role,
        user_dept_id=current_user.department_id
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Guardrail Violation: {msg}")

    result = SQLExecutor.execute(db, req.sql, limit=req.limit or 500)
    return result.to_dict()
