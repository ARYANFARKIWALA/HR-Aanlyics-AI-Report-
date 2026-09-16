"""FastAPI Routes for Module 7 - SQL Validator & Security Engine."""

import json
import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.models import User
from backend.database.models_validation import SQLValidationAuditLog
from backend.auth.dependencies import get_current_user, require_permission
from sql_validator.schemas import (
    SQLValidationRequest,
    SQLValidationResponse,
    ValidationPolicy,
)
from sql_validator.service import SQLValidatorService
from sql_validator.policy_engine import DEFAULT_POLICY, SAFE_FUNCTIONS, FORBIDDEN_FUNCTIONS

router = APIRouter(prefix="/api/sql-validator", tags=["SQL Validator & Security Gate"])


@router.post("/validate", response_model=SQLValidationResponse)
def validate_sql(
    request: SQLValidationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submits SQL query for full zero-trust AST validation.
    Issues cryptographic validation_id if approved.
    HARD INVARIANT: NEVER executes SQL.
    """
    service = SQLValidatorService(db=db)
    # Ensure request carries authenticated user context
    request.user_id = current_user.id
    request.username = current_user.username
    request.user_role = current_user.role
    request.department_id = current_user.department_id

    result = service.validate_query(request)
    return result


@router.post("/check", response_model=SQLValidationResponse)
def check_sql(
    request: SQLValidationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Pre-flight validation check for UI sandboxes without issuing an execution token."""
    service = SQLValidatorService(db=db)
    request.user_id = current_user.id
    request.username = current_user.username
    request.user_role = current_user.role
    result = service.validate_query(request)
    return result


@router.get("/tokens/{validation_id}")
def get_validation_token_status(
    validation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Inspects validation token status and expiration."""
    entry = db.query(SQLValidationAuditLog).filter(
        SQLValidationAuditLog.validation_id == validation_id
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail=f"Validation token '{validation_id}' not found.")

    now = datetime.datetime.now(datetime.UTC)
    expires_at = entry.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=datetime.UTC)

    is_expired = now > expires_at
    remaining_sec = max(0, int((expires_at - now).total_seconds())) if not is_expired else 0

    return {
        "validation_id": entry.validation_id,
        "database_id": entry.database_id,
        "status": entry.status,
        "is_expired": is_expired,
        "remaining_seconds": remaining_sec,
        "risk_score": entry.risk_score,
        "risk_level": entry.risk_level,
        "sql_hash": entry.sql_hash,
        "sanitized_sql": entry.sanitized_sql,
        "username": entry.username,
        "created_at": entry.created_at.isoformat() if entry.created_at else None
    }


@router.get("/audit")
def get_validation_audit_logs(
    limit: int = 50,
    current_user: User = Depends(require_permission("admin:audit")),
    db: Session = Depends(get_db)
):
    """Returns historical validation decisions and audit logs."""
    logs = db.query(SQLValidationAuditLog).order_by(
        SQLValidationAuditLog.created_at.desc()
    ).limit(limit).all()

    results = []
    for l in logs:
        results.append({
            "id": l.id,
            "validation_id": l.validation_id,
            "database_id": l.database_id,
            "username": l.username,
            "user_role": l.user_role,
            "status": l.status,
            "risk_score": l.risk_score,
            "risk_level": l.risk_level,
            "sql_hash": l.sql_hash,
            "raw_sql": l.raw_sql,
            "violations": json.loads(l.violations) if l.violations else [],
            "warnings": json.loads(l.warnings) if l.warnings else [],
            "created_at": l.created_at.isoformat() if l.created_at else None,
            "expires_at": l.expires_at.isoformat() if l.expires_at else None,
        })
    return {"validation_logs": results}


@router.get("/policies")
def get_policies(current_user: User = Depends(get_current_user)):
    """Returns active security policies and safe function allowlists."""
    return {
        "policy": DEFAULT_POLICY.model_dump(),
        "safe_functions": sorted(list(SAFE_FUNCTIONS)),
        "forbidden_functions": sorted(list(FORBIDDEN_FUNCTIONS))
    }
