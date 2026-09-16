"""FastAPI REST API routes for Module 12 - Reports Lifecycle, Versioning, Sharing, and History."""


from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from backend.auth.authorization import AuthorizationService
from backend.auth.dependencies import get_current_user
from backend.database.connection import get_db
from backend.database.models import User
from reports_lifecycle.execution_service import ReportExecutionService
from reports_lifecycle.export_service import ReportExportService
from reports_lifecycle.report_service import ReportLifecycleService
from reports_lifecycle.schemas import (
    ReportAccessCreateRequest,
    ReportAccessResponse,
    ReportCreateRequest,
    ReportDuplicateRequest,
    ReportExecutionResponse,
    ReportResponse,
    ReportRunRequest,
    ReportRunResponse,
    ReportUpdateRequest,
    ReportVersionResponse,
)
from reports_lifecycle.sharing_service import ReportSharingService
from reports_lifecycle.version_service import ReportVersionService

router = APIRouter(prefix="/api/reports-lifecycle", tags=["Module 12 - Reports Lifecycle"])


@router.get("", response_model=list[ReportResponse])
def list_reports(
    category: str | None = Query(None),
    search: str | None = Query(None),
    include_archived: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists saved reports accessible to current user."""
    reports = ReportLifecycleService.list_reports(
        db=db,
        user=current_user,
        category=category,
        search=search,
        include_archived=include_archived
    )
    return [ReportResponse.model_validate(r) for r in reports]


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def create_report(
    request: ReportCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Creates a new saved report with initial version snapshot."""
    if not AuthorizationService.has_permission(db, current_user, "report:create"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User lacks required 'report:create' capability."
        )
    report = ReportLifecycleService.create_report(db=db, req=request, user=current_user)
    return ReportResponse.model_validate(report)


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves a single saved report checking viewing clearance."""
    try:
        report = ReportLifecycleService.get_report(db=db, report_id=report_id, user=current_user)
        return ReportResponse.model_validate(report)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Report '{report_id}' not found.")
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))


@router.put("/{report_id}", response_model=ReportResponse)
def update_report(
    report_id: str,
    request: ReportUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Updates an existing report and creates an immutable version snapshot."""
    try:
        updated = ReportLifecycleService.update_report(
            db=db,
            report_id=report_id,
            req=request,
            user=current_user
        )
        return ReportResponse.model_validate(updated)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Report '{report_id}' not found.")
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))


@router.post("/{report_id}/duplicate", response_model=ReportResponse)
def duplicate_report(
    report_id: str,
    request: ReportDuplicateRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Duplicates an existing report for the current user."""
    try:
        new_title = request.new_title if request else None
        dup = ReportLifecycleService.duplicate_report(
            db=db,
            report_id=report_id,
            user=current_user,
            new_title=new_title
        )
        return ReportResponse.model_validate(dup)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Report '{report_id}' not found.")
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))


@router.post("/{report_id}/archive", response_model=ReportResponse)
def archive_report(
    report_id: str,
    archive: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Archives or unarchives a report (ADMIN clearance required)."""
    try:
        archived = ReportLifecycleService.archive_report(
            db=db,
            report_id=report_id,
            user=current_user,
            archive=archive
        )
        return ReportResponse.model_validate(archived)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Report '{report_id}' not found.")
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))


@router.delete("/{report_id}")
def delete_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-deletes a report (ADMIN clearance required)."""
    try:
        ReportLifecycleService.delete_report(db=db, report_id=report_id, user=current_user)
        return {"status": "deleted", "report_id": report_id}
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Report '{report_id}' not found.")
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))


# =========================================================================
# Versions & Non-Destructive Restore
# =========================================================================

@router.get("/{report_id}/versions", response_model=list[ReportVersionResponse])
def list_versions(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists all historical version snapshots for a report."""
    try:
        report = ReportLifecycleService.get_report(db=db, report_id=report_id, user=current_user)
        versions = ReportVersionService.list_versions(db=db, report=report)
        return [ReportVersionResponse.model_validate(v) for v in versions]
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Report '{report_id}' not found.")
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))


@router.post("/{report_id}/versions/{version_number}/restore", response_model=ReportResponse)
def restore_version(
    report_id: str,
    version_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Non-destructively restores a previous version by creating a new version snapshot."""
    try:
        report = ReportLifecycleService.get_report(db=db, report_id=report_id, user=current_user)
        level = getattr(report, "user_access_level", "NONE")
        if not ReportSharingService.can_edit(level):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="EDIT permission required to restore versions.")
        restored = ReportVersionService.restore_version(db=db, report=report, version_number=version_number, modifier=current_user)
        return ReportResponse.model_validate(restored)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Report '{report_id}' not found.")
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))


# =========================================================================
# Sharing & ACLs
# =========================================================================

@router.get("/{report_id}/access", response_model=list[ReportAccessResponse])
def list_report_access(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists granular access rules (ACLs) for a report."""
    try:
        report = ReportLifecycleService.get_report(db=db, report_id=report_id, user=current_user)
        rules = ReportSharingService.list_access_rules(db=db, report=report)
        return [ReportAccessResponse.model_validate(r) for r in rules]
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Report '{report_id}' not found.")
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))


@router.post("/{report_id}/access", response_model=ReportAccessResponse)
def grant_report_access(
    report_id: str,
    request: ReportAccessCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Grants or updates sharing permissions for a user or role (ADMIN clearance required)."""
    try:
        report = ReportLifecycleService.get_report(db=db, report_id=report_id, user=current_user)
        level = getattr(report, "user_access_level", "NONE")
        if not ReportSharingService.can_admin(level):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ADMIN clearance required to manage sharing ACLs.")
        rule = ReportSharingService.grant_access(db=db, report=report, req=request, granter=current_user)
        return ReportAccessResponse.model_validate(rule)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Report '{report_id}' not found.")
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))


@router.delete("/{report_id}/access/{access_id}")
def revoke_report_access(
    report_id: str,
    access_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revokes a sharing ACL rule."""
    try:
        report = ReportLifecycleService.get_report(db=db, report_id=report_id, user=current_user)
        level = getattr(report, "user_access_level", "NONE")
        if not ReportSharingService.can_admin(level):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ADMIN clearance required to revoke ACLs.")
        success = ReportSharingService.revoke_access(db=db, report=report, access_id=access_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Access rule {access_id} not found.")
        return {"status": "revoked", "access_id": access_id}
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Report '{report_id}' not found.")
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))


# =========================================================================
# Re-run Revalidation Execution & History
# =========================================================================

@router.post("/{report_id}/run", response_model=ReportRunResponse)
def run_report(
    report_id: str,
    request: ReportRunRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Re-executes a report strictly adhering to the Re-run Revalidation Invariant."""
    try:
        report = ReportLifecycleService.get_report(db=db, report_id=report_id, user=current_user)
        res = ReportExecutionService.run_report(db=db, report=report, user=current_user, run_req=request)
        return res
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Report '{report_id}' not found.")
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))


@router.get("/{report_id}/executions", response_model=list[ReportExecutionResponse])
def get_report_executions(
    report_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists historical execution records for a report."""
    try:
        report = ReportLifecycleService.get_report(db=db, report_id=report_id, user=current_user)
        records = ReportExecutionService.list_executions(db=db, report=report, limit=limit)
        return [ReportExecutionResponse.model_validate(r) for r in records]
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Report '{report_id}' not found.")
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))


# =========================================================================
# Masked Multi-Format Export (CSV, Excel, PDF)
# =========================================================================

@router.post("/{report_id}/export/{export_format}")
def export_report(
    report_id: str,
    export_format: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generates an export (CSV, Excel, or PDF) with strict Column-Level Security (CLS) masking."""
    fmt = export_format.lower()
    if fmt not in ["csv", "excel", "pdf"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Supported export formats are 'csv', 'excel', 'pdf'.")

    # Verify user has report:export capability
    if not AuthorizationService.has_permission(db, current_user, "report:export"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing required 'report:export' system capability.")

    try:
        report = ReportLifecycleService.get_report(db=db, report_id=report_id, user=current_user)
        level = getattr(report, "user_access_level", "NONE")
        if not ReportSharingService.can_export(level):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Report ACL requires at least EXPORT clearance.")

        # Re-run execution pipeline to get fresh sanitized data
        run_res = ReportExecutionService.run_report(db=db, report=report, user=current_user)
        if run_res.status != "SUCCESS":
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Query execution failed: {run_res.error}")

        safe_title = "".join(c for c in report.title if c.isalnum() or c in (" ", "_", "-")).rstrip()
        filename_base = f"{safe_title.replace(' ', '_')}_{report.report_id}"

        if fmt == "csv":
            content = ReportExportService.export_csv(
                report=report,
                columns=run_res.columns,
                rows=run_res.rows,
                user=current_user
            )
            return Response(
                content=content,
                media_type="text/csv",
                headers={"Content-Disposition": f'attachment; filename="{filename_base}.csv"'}
            )
        elif fmt == "excel":
            content = ReportExportService.export_excel(
                report=report,
                columns=run_res.columns,
                rows=run_res.rows,
                user=current_user
            )
            return Response(
                content=content,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f'attachment; filename="{filename_base}.xlsx"'}
            )
        elif fmt == "pdf":
            content = ReportExportService.export_pdf(
                report=report,
                columns=run_res.columns,
                rows=run_res.rows,
                user=current_user
            )
            return Response(
                content=content,
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{filename_base}.pdf"'}
            )
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Report '{report_id}' not found.")
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
