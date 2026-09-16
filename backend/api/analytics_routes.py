"""Analytics and KPI metrics API routes (Module 9)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from analytics.metrics import HRMetricsCalculator
from analytics.schemas import AnalyticsRequest, AnalyticsResponse
from analytics.service import HRAnalyticsService
from security.audit import AuditLogger

from ..auth.dependencies import get_current_user, require_permission, require_role
from ..database.connection import get_db
from ..database.models import User
from ..database.models_analytics import AnalyticsAuditLog

router = APIRouter(prefix="/api/analytics", tags=["HR Analytics Engine"])


@router.post("/analyze", response_model=AnalyticsResponse)
def analyze_dataset(
    request: AnalyticsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Executes complete deterministic analytics pipeline on dataset or execution_id.
    HARD INVARIANT: Operates strictly on authorized datasets, never executes raw queries.
    """
    service = HRAnalyticsService(db=db)
    result = service.analyze(request=request, user=current_user)
    return result


@router.get("/kpis")
def get_executive_kpis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns top-level executive HR KPIs."""
    return HRMetricsCalculator.get_executive_summary_kpis(db)


@router.get("/attrition")
def get_department_attrition(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns departmental attrition and turnover metrics."""
    return HRMetricsCalculator.get_attrition_by_department(db)


@router.get("/audit-logs")
def get_audit_logs(
    limit: int = 50,
    current_user: User = Depends(require_role(["admin", "executive"])),
    db: Session = Depends(get_db)
):
    """Returns compliance query audit logs (admin / executive)."""
    return AuditLogger.get_recent_logs(db, limit=limit)


@router.get("/audit")
def get_analytics_audit(
    limit: int = 50,
    current_user: User = Depends(require_permission("admin:audit")),
    db: Session = Depends(get_db)
):
    """Returns analytics run history."""
    logs = db.query(AnalyticsAuditLog).order_by(
        AnalyticsAuditLog.created_at.desc()
    ).limit(limit).all()
    results = []
    for l in logs:
        results.append({
            "analysis_id": l.analysis_id,
            "execution_id": l.execution_id,
            "username": l.username,
            "dataset_shape": l.dataset_shape,
            "insights_count": l.insights_generated_count,
            "quality_score": l.data_quality_score,
            "created_at": l.created_at.isoformat() if l.created_at else None
        })
    return {"analytics_history": results}
