"""Module 4: Business Rule Management FastAPI Endpoints.

Implements all CRUD, approval, rejection, versioning, conflict detection,
and active rule query endpoints.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.models import User
from backend.auth.dependencies import get_current_user, require_role
from business_rules.service import BusinessRuleService
from business_rules.schemas import (
    RuleCreateRequest, RuleUpdateRequest, RuleApprovalRequest,
    RuleRejectionRequest, RuleVersionCreateRequest
)
from business_rules.conflict_detector import RuleConflictDetector
from business_rules.duplicate_detector import RuleDuplicateDetector
from business_rules.validator import RuleValidationError

router = APIRouter(prefix="/api/business-rules", tags=["Module 4: Business Rule Management"])


def success_response(data: Any) -> Dict[str, Any]:
    return {"success": True, "data": data}


def error_response(code: str, message: str, status_code: int = 400):
    raise HTTPException(
        status_code=status_code,
        detail={"success": False, "error": {"code": code, "message": message}}
    )


# -------------------------------------------------------------
# 1. Statistics & Search
# -------------------------------------------------------------
@router.get("/stats")
def get_dashboard_stats(
    database_id: str = Query("sqlite_hr_default"),
    db: Session = Depends(get_db)
):
    """Returns rule counts by status, priority, and confidence."""
    service = BusinessRuleService(db)
    stats = service.get_dashboard_stats(database_id=database_id)
    return success_response(stats)


@router.get("/active")
def get_active_rules(
    database_id: str = Query("sqlite_hr_default"),
    db: Session = Depends(get_db)
):
    """Exposes ONLY active and current rules for Module 5 RAG indexing."""
    service = BusinessRuleService(db)
    rules = service.get_active_rules(database_id=database_id)
    return success_response([
        {
            "id": r.id,
            "rule_code": r.rule_code,
            "rule_name": r.rule_name,
            "rule_type": r.rule_type,
            "rule_expression": r.rule_expression,
            "natural_language_rule": r.natural_language_rule,
            "priority": r.priority,
            "mandatory": r.mandatory,
            "table_name": r.table_name,
            "column_name": r.column_name,
            "version": r.version
        }
        for r in rules
    ])


@router.get("/conflicts")
def scan_conflicts(
    rule_expression: str = Query(..., min_length=2),
    table_name: Optional[str] = Query(None),
    column_name: Optional[str] = Query(None),
    database_id: str = Query("sqlite_hr_default"),
    db: Session = Depends(get_db)
):
    """Scans for logical contradictions against existing active rules."""
    conflicts = RuleConflictDetector.detect_conflicts(
        candidate_rule={
            "rule_expression": rule_expression,
            "table_name": table_name,
            "column_name": column_name,
            "database_id": database_id
        },
        db=db,
        database_id=database_id
    )
    return success_response({"has_conflicts": len(conflicts) > 0, "conflicts": conflicts})


@router.get("/duplicates")
def scan_duplicates(
    rule_expression: str = Query(..., min_length=2),
    natural_language_rule: Optional[str] = Query(""),
    database_id: str = Query("sqlite_hr_default"),
    db: Session = Depends(get_db)
):
    """Scans for identical or highly similar business rules."""
    duplicates = RuleDuplicateDetector.detect_duplicates(
        candidate_rule={
            "rule_expression": rule_expression,
            "natural_language_rule": natural_language_rule,
            "database_id": database_id
        },
        db=db,
        database_id=database_id
    )
    return success_response({"has_duplicates": len(duplicates) > 0, "duplicates": duplicates})


@router.post("/detect-from-sql")
def detect_rules_from_sql(
    database_id: str = Query("sqlite_hr_default"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mines Module 2 SQL repository reports to discover candidate business rules."""
    service = BusinessRuleService(db)
    detected = service.detect_rules_from_sql_repository(database_id=database_id)
    return success_response({
        "detected_count": len(detected),
        "rules": [{"id": r.id, "rule_code": r.rule_code, "rule_name": r.rule_name} for r in detected]
    })


# -------------------------------------------------------------
# 2. Rule CRUD & Listings
# -------------------------------------------------------------
@router.post("")
def create_business_rule(
    request: RuleCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Creates a new business rule with version 1 and audit logging."""
    service = BusinessRuleService(db)
    try:
        rule = service.create_rule(request.dict(), user_name=current_user.username)
        return success_response({
            "id": rule.id,
            "rule_code": rule.rule_code,
            "rule_name": rule.rule_name,
            "status": rule.status,
            "version": rule.version
        })
    except RuleValidationError as ve:
        error_response("VALIDATION_ERROR", str(ve), status_code=400)
    except Exception as e:
        error_response("INTERNAL_ERROR", str(e), status_code=500)


@router.get("")
def list_business_rules(
    database_id: str = Query("sqlite_hr_default"),
    status: Optional[str] = Query(None),
    rule_type: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    table_name: Optional[str] = Query(None),
    mandatory: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Lists business rules with facet filters."""
    service = BusinessRuleService(db)
    rules = service.get_rules(
        database_id=database_id,
        status=status,
        rule_type=rule_type,
        priority=priority,
        table_name=table_name,
        mandatory=mandatory,
        search=search
    )
    return success_response([
        {
            "id": r.id,
            "rule_code": r.rule_code,
            "rule_name": r.rule_name,
            "rule_type": r.rule_type,
            "rule_expression": r.rule_expression,
            "natural_language_rule": r.natural_language_rule,
            "status": r.status,
            "priority": r.priority,
            "mandatory": r.mandatory,
            "scope": r.scope,
            "table_name": r.table_name,
            "column_name": r.column_name,
            "confidence_score": r.confidence_score,
            "version": r.version,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rules
    ])


@router.get("/{rule_id}")
def get_rule_detail(
    rule_id: int,
    db: Session = Depends(get_db)
):
    """Returns deep details for a rule including version history and audit log."""
    service = BusinessRuleService(db)
    detail = service.get_rule_detail(rule_id)
    if not detail:
        error_response("RULE_NOT_FOUND", f"Business rule ID {rule_id} not found", status_code=404)
    return success_response(detail)


@router.put("/{rule_id}")
def update_business_rule(
    rule_id: int,
    request: RuleUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates a rule. If active, creates an immutable new version."""
    service = BusinessRuleService(db)
    try:
        updated = service.update_rule(
            rule_id=rule_id,
            data=request.dict(exclude_unset=True),
            user_name=current_user.username
        )
        return success_response({
            "id": updated.id,
            "rule_code": updated.rule_code,
            "rule_name": updated.rule_name,
            "version": updated.version,
            "status": updated.status
        })
    except RuleValidationError as ve:
        error_response("VALIDATION_ERROR", str(ve), status_code=400)
    except ValueError as ve:
        error_response("UPDATE_ERROR", str(ve), status_code=400)


# -------------------------------------------------------------
# 3. Lifecycle Transitions (Approve, Reject, Activate, Deactivate)
# -------------------------------------------------------------
@router.post("/{rule_id}/approve")
def approve_rule(
    rule_id: int,
    request: RuleApprovalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Approves a rule into ACTIVE status."""
    service = BusinessRuleService(db)
    try:
        approved = service.approve_rule(
            rule_id=rule_id,
            comment=request.comment or "Approved by admin.",
            user_name=current_user.username
        )
        return success_response({
            "id": approved.id,
            "rule_code": approved.rule_code,
            "status": approved.status,
            "approved_at": approved.approved_at.isoformat() if approved.approved_at else None
        })
    except ValueError as ve:
        error_response("APPROVAL_ERROR", str(ve), status_code=400)


@router.post("/{rule_id}/reject")
def reject_rule(
    rule_id: int,
    request: RuleRejectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Rejects a rule with documented rationale (rule record is preserved)."""
    service = BusinessRuleService(db)
    try:
        rejected = service.reject_rule(
            rule_id=rule_id,
            reason=request.reason,
            user_name=current_user.username
        )
        return success_response({
            "id": rejected.id,
            "rule_code": rejected.rule_code,
            "status": rejected.status,
            "rejection_reason": rejected.rejection_reason
        })
    except ValueError as ve:
        error_response("REJECTION_ERROR", str(ve), status_code=400)


@router.post("/{rule_id}/activate")
def activate_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Activates an approved rule."""
    service = BusinessRuleService(db)
    try:
        active = service.activate_rule(rule_id=rule_id, user_name=current_user.username)
        return success_response({"id": active.id, "status": active.status})
    except ValueError as ve:
        error_response("ACTIVATION_ERROR", str(ve), status_code=400)


@router.post("/{rule_id}/deactivate")
def deactivate_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deactivates a rule."""
    service = BusinessRuleService(db)
    try:
        inactive = service.deactivate_rule(rule_id=rule_id, user_name=current_user.username)
        return success_response({"id": inactive.id, "status": inactive.status})
    except ValueError as ve:
        error_response("DEACTIVATION_ERROR", str(ve), status_code=400)
