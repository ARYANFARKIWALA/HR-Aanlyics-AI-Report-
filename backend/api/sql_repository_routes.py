"""Module 2: Existing SQL Repository & Knowledge Management API Endpoints.

Implements all CRUD, validation, version control, approval workflows,
bulk file import, and RAG knowledge generation with standard JSON envelopes:
  Success: { "success": true, "data": { ... } }
  Error:   { "success": false, "error": { "code": "...", "message": "..." } }
"""

from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from rag.sql_knowledge_builder import SQLKnowledgeBuilder

from ..auth.dependencies import get_current_user, require_role
from ..database.connection import get_db
from ..database.models import User
from ..database.models_repo import SQLCategory, SQLReport
from ..services.sql_repository_service import SQLRepositoryService

router = APIRouter(prefix="/api/sql-reports", tags=["Module 2: SQL Knowledge Repository"])


# -------------------------------------------------------------
# Request & Response Schemas
# -------------------------------------------------------------
class ReportCreateRequest(BaseModel):
    report_name: str = Field(..., min_length=1)
    sql_query: str = Field(..., min_length=1)
    database_id: str
    description: str | None = ""
    business_purpose: str | None = ""
    category: str | None = "Other"
    tags: list[str] | None = []
    organization_id: str | None = "org_default"


class ReportUpdateRequest(BaseModel):
    report_name: str | None = None
    description: str | None = None
    business_purpose: str | None = None
    category: str | None = None
    sql_query: str | None = None
    change_description: str | None = "Updated report."


class ApprovalDecisionRequest(BaseModel):
    comment: str | None = "Approved."


class RejectionDecisionRequest(BaseModel):
    reason: str = Field(..., min_length=1)


class VersionCompareRequest(BaseModel):
    version_1: int
    version_2: int


# Standard Response Helpers
def success_response(data: Any) -> dict[str, Any]:
    return {"success": True, "data": data}


def error_response(code: str, message: str, status_code: int = 400):
    raise HTTPException(
        status_code=status_code,
        detail={"success": False, "error": {"code": code, "message": message}}
    )


# -------------------------------------------------------------
# 1. Statistics & Categories
# -------------------------------------------------------------
@router.get("/stats")
def get_repository_stats(
    organization_id: str = "org_default",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns repository dashboard statistics (total, approved, pending, invalid, archived)."""
    stats = SQLRepositoryService.get_dashboard_stats(db, organization_id=organization_id)
    return success_response(stats)


@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    """Lists predefined and custom categories."""
    predefined = [
        "Headcount", "Attrition", "Recruitment", "Attendance", "Leave",
        "Salary", "Compensation", "Performance", "Employee Demographics",
        "Department", "Job Role", "Location", "Tenure", "Other"
    ]
    custom_records = db.query(SQLCategory).all()
    all_cats = list(dict.fromkeys(predefined + [c.name for c in custom_records]))
    return success_response(all_cats)


# -------------------------------------------------------------
# 2. Add / Create Report (Manual SQL)
# -------------------------------------------------------------
@router.post("")
def create_sql_report(
    req: ReportCreateRequest,
    current_user: User = Depends(require_role(["admin", "hr_manager"])),
    db: Session = Depends(get_db)
):
    """Imports a single existing SQL report into the repository."""
    if not req.sql_query.strip():
        error_response("EMPTY_SQL_ERROR", "The SQL query cannot be empty.", 400)

    try:
        report, dup_info = SQLRepositoryService.create_report(
            session=db,
            report_name=req.report_name,
            sql_query=req.sql_query,
            database_id=req.database_id,
            user=current_user,
            description=req.description or "",
            business_purpose=req.business_purpose or "",
            category=req.category or "Other",
            tags=req.tags,
            organization_id=req.organization_id or "org_default"
        )
        return success_response({
            "report_id": report.id,
            "report_code": report.report_code,
            "status": report.status,
            "is_valid": report.is_valid,
            "validation_error": report.validation_error,
            "version": report.version,
            "complexity_level": report.metadata_rel.complexity_level if report.metadata_rel else "LOW",
            "duplicate_info": dup_info
        })
    except Exception as exc:
        error_response("SQL_IMPORT_ERROR", str(exc), 500)


# -------------------------------------------------------------
# 3. List & Search Reports
# -------------------------------------------------------------
@router.get("")
def list_and_search_reports(
    q: str | None = None,
    database_id: str | None = None,
    category: str | None = None,
    status_filter: str | None = None,
    complexity: str | None = None,
    uses_effective_dating: bool | None = None,
    uses_security_filter: bool | None = None,
    organization_id: str = "org_default",
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Searches and filters existing SQL reports in the repository."""
    # Viewers can only view APPROVED reports
    effective_status = status_filter
    if current_user.role == "viewer":
        effective_status = "APPROVED"

    reports = SQLRepositoryService.search_reports(
        session=db,
        query=q,
        database_id=database_id,
        category=category,
        status=effective_status,
        complexity=complexity,
        uses_effective_dating=uses_effective_dating,
        uses_security_filter=uses_security_filter,
        organization_id=organization_id,
        limit=limit
    )

    results = []
    for r in reports:
        meta = r.metadata_rel
        results.append({
            "id": r.id,
            "report_code": r.report_code,
            "report_name": r.report_name,
            "category": r.category,
            "database_id": r.database_id,
            "status": r.status,
            "version": r.version,
            "is_valid": r.is_valid,
            "complexity_level": meta.complexity_level if meta else "LOW",
            "table_count": meta.table_count if meta else 0,
            "uses_effective_dating": meta.uses_effective_dating if meta else False,
            "uses_security_filter": meta.uses_security_filter if meta else False,
            "updated_at": r.updated_at.isoformat() if r.updated_at else ""
        })

    return success_response(results)


# -------------------------------------------------------------
# 4. Get Report Details
# -------------------------------------------------------------
@router.get("/{report_id}")
def get_report_detail(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves full report details, metadata, parameters, and version history."""
    report = db.query(SQLReport).filter(SQLReport.id == report_id).first()
    if not report:
        error_response("REPORT_NOT_FOUND", f"Report with ID {report_id} does not exist.", 404)

    # Viewers can only view APPROVED reports
    if current_user.role == "viewer" and report.status != "APPROVED":
        error_response("UNAUTHORIZED_ACCESS", "Viewer role cannot access unapproved reports.", 403)

    meta = report.metadata_rel
    import json
    metadata_dict = {}
    if meta:
        metadata_dict = {
            "table_count": meta.table_count,
            "column_count": meta.column_count,
            "join_count": meta.join_count,
            "cte_count": meta.cte_count,
            "subquery_count": meta.subquery_count,
            "aggregation_count": meta.aggregation_count,
            "uses_effective_dating": meta.uses_effective_dating,
            "uses_security_filter": meta.uses_security_filter,
            "has_date_logic": meta.has_date_logic,
            "has_business_logic": meta.has_business_logic,
            "complexity_level": meta.complexity_level,
            "complexity_score": meta.complexity_score,
            "tables": json.loads(meta.tables_json) if meta.tables_json else [],
            "columns": json.loads(meta.columns_json) if meta.columns_json else [],
            "joins": json.loads(meta.joins_json) if meta.joins_json else [],
            "filters": json.loads(meta.filters_json) if meta.filters_json else [],
            "aggregations": json.loads(meta.aggregations_json) if meta.aggregations_json else [],
            "effective_dating_details": json.loads(meta.effective_dating_details) if meta.effective_dating_details else [],
            "security_filters_details": json.loads(meta.security_filters_details) if meta.security_filters_details else [],
            "business_logic_details": json.loads(meta.business_logic_details) if meta.business_logic_details else [],
        }

    params = [
        {
            "name": p.parameter_name,
            "type": p.parameter_type,
            "required": p.required,
            "default_value": p.default_value,
            "description": p.description
        }
        for p in report.parameters
    ]

    versions = [
        {
            "version_number": v.version_number,
            "change_description": v.change_description,
            "created_at": v.created_at.isoformat() if v.created_at else ""
        }
        for v in report.versions
    ]

    approvals = [
        {
            "action": a.action,
            "comment": a.comment,
            "created_at": a.created_at.isoformat() if a.created_at else ""
        }
        for a in report.approvals
    ]

    return success_response({
        "id": report.id,
        "report_code": report.report_code,
        "organization_id": report.organization_id,
        "database_id": report.database_id,
        "report_name": report.report_name,
        "description": report.description,
        "business_purpose": report.business_purpose,
        "category": report.category,
        "status": report.status,
        "version": report.version,
        "is_valid": report.is_valid,
        "validation_error": report.validation_error,
        "original_sql": report.sql_query,
        "normalized_sql": report.normalized_sql,
        "sql_hash": report.sql_hash,
        "metadata": metadata_dict,
        "parameters": params,
        "versions": versions,
        "approvals": approvals,
        "created_at": report.created_at.isoformat() if report.created_at else "",
        "updated_at": report.updated_at.isoformat() if report.updated_at else ""
    })


# -------------------------------------------------------------
# 5. Update Report (Creates Version if SQL Changes)
# -------------------------------------------------------------
@router.put("/{report_id}")
def update_sql_report(
    report_id: int,
    req: ReportUpdateRequest,
    current_user: User = Depends(require_role(["admin", "hr_manager"])),
    db: Session = Depends(get_db)
):
    """Updates report metadata or creates a new version if SQL query was modified."""
    try:
        updated = SQLRepositoryService.update_report(
            session=db,
            report_id=report_id,
            user=current_user,
            report_name=req.report_name,
            description=req.description,
            business_purpose=req.business_purpose,
            category=req.category,
            sql_query=req.sql_query,
            change_description=req.change_description or "Updated report."
        )
        return success_response({
            "message": f"Report '{updated.report_name}' updated successfully.",
            "version": updated.version,
            "status": updated.status,
            "is_valid": updated.is_valid
        })
    except KeyError as exc:
        error_response("REPORT_NOT_FOUND", str(exc), 404)
    except Exception as exc:
        error_response("REPORT_UPDATE_ERROR", str(exc), 500)


# -------------------------------------------------------------
# 6. Workflow Actions (Approve, Reject, Archive)
# -------------------------------------------------------------
@router.post("/{report_id}/approve")
def approve_report(
    report_id: int,
    req: ApprovalDecisionRequest,
    current_user: User = Depends(require_role(["admin", "hr_manager"])),
    db: Session = Depends(get_db)
):
    """Approves a report for active RAG knowledge use."""
    try:
        approved = SQLRepositoryService.approve_report(
            session=db,
            report_id=report_id,
            user=current_user,
            comment=req.comment or "Approved for RAG knowledge repository."
        )
        return success_response({
            "message": f"Report '{approved.report_name}' approved successfully.",
            "status": approved.status
        })
    except ValueError as exc:
        error_response("INVALID_REPORT_APPROVAL", str(exc), 400)
    except KeyError as exc:
        error_response("REPORT_NOT_FOUND", str(exc), 404)


@router.post("/{report_id}/reject")
def reject_report(
    report_id: int,
    req: RejectionDecisionRequest,
    current_user: User = Depends(require_role(["admin", "hr_manager"])),
    db: Session = Depends(get_db)
):
    """Rejects a report and resets its status."""
    try:
        rejected = SQLRepositoryService.reject_report(
            session=db,
            report_id=report_id,
            user=current_user,
            reason=req.reason
        )
        return success_response({
            "message": f"Report '{rejected.report_name}' rejected.",
            "status": rejected.status
        })
    except KeyError as exc:
        error_response("REPORT_NOT_FOUND", str(exc), 404)


@router.post("/{report_id}/archive")
def archive_report(
    report_id: int,
    req: ApprovalDecisionRequest,
    current_user: User = Depends(require_role(["admin", "hr_manager"])),
    db: Session = Depends(get_db)
):
    """Archives a report, removing it from active RAG knowledge."""
    try:
        archived = SQLRepositoryService.archive_report(
            session=db,
            report_id=report_id,
            user=current_user,
            reason=req.comment or "Archived."
        )
        return success_response({
            "message": f"Report '{archived.report_name}' archived.",
            "status": archived.status
        })
    except KeyError as exc:
        error_response("REPORT_NOT_FOUND", str(exc), 404)


# -------------------------------------------------------------
# 7. Version Comparison
# -------------------------------------------------------------
@router.post("/{report_id}/versions/compare")
def compare_report_versions(
    report_id: int,
    req: VersionCompareRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Compares two historical versions of a SQL report with unified diff."""
    try:
        comparison = SQLRepositoryService.compare_versions(
            session=db,
            report_id=report_id,
            v1_num=req.version_1,
            v2_num=req.version_2
        )
        return success_response(comparison)
    except KeyError as exc:
        error_response("VERSION_NOT_FOUND", str(exc), 404)


# -------------------------------------------------------------
# 8. Single File & Bulk File Uploads
# -------------------------------------------------------------
@router.post("/import")
async def import_sql_file(
    database_id: str = Form(...),
    category: str | None = Form("Other"),
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(["admin", "hr_manager"])),
    db: Session = Depends(get_db)
):
    """Imports queries from an uploaded .sql or .txt file."""
    content_bytes = await file.read()
    content_str = content_bytes.decode("utf-8", errors="replace")

    results = SQLRepositoryService.import_sql_content(
        session=db,
        content=content_str,
        database_id=database_id,
        user=current_user,
        filename=file.filename,
        default_category=category or "Other"
    )

    imported_data = [
        {
            "id": r.id,
            "report_code": r.report_code,
            "report_name": r.report_name,
            "status": r.status,
            "is_valid": r.is_valid,
            "is_duplicate": dup["is_duplicate"]
        }
        for r, dup in results
    ]

    return success_response({
        "filename": file.filename,
        "total_queries": len(imported_data),
        "imported_queries": imported_data
    })


@router.post("/bulk-import")
async def bulk_import_sql_files(
    database_id: str = Form(...),
    files: list[UploadFile] = File(...),
    current_user: User = Depends(require_role(["admin", "hr_manager"])),
    db: Session = Depends(get_db)
):
    """Bulk imports multiple .sql files with pre-validation and duplicate detection summary."""
    files_dict = {}
    for f in files:
        b = await f.read()
        files_dict[f.filename] = b.decode("utf-8", errors="replace")

    summary = SQLRepositoryService.bulk_import(
        session=db,
        files_dict=files_dict,
        database_id=database_id,
        user=current_user
    )

    return success_response(summary)


# -------------------------------------------------------------
# 9. RAG Knowledge Document Output (Module 5 preparation)
# -------------------------------------------------------------
@router.get("/{report_id}/knowledge")
def get_report_rag_knowledge(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns the structured, LlamaIndex-ready knowledge representation of an approved report."""
    report = db.query(SQLReport).filter(SQLReport.id == report_id).first()
    if not report:
        error_response("REPORT_NOT_FOUND", f"Report #{report_id} not found.", 404)

    doc = SQLKnowledgeBuilder.build_knowledge_document(report, report.metadata_rel)
    return success_response(doc.to_dict())
