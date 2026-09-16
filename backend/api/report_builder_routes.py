"""FastAPI Routes for Module 10 - Report Builder & Visualization."""

from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth.dependencies import get_current_user
from backend.database.models import User
from report_builder.schemas import BuiltReport, ReportDefinition
from report_builder.service import ReportBuilderService
from report_builder.template_manager import TemplateManager

router = APIRouter(prefix="/api/report-builder", tags=["Report Builder & Visualization"])


class BuildReportRequest(BaseModel):
    definition: ReportDefinition | None = None
    template_key: str | None = None
    dataset: list[dict[str, Any]]
    active_filters: dict[str, Any] | None = None


@router.get("/templates")
def list_report_templates(current_user: User = Depends(get_current_user)):
    """Lists pre-configured executive HR report templates."""
    return {"templates": TemplateManager.list_templates()}


@router.post("/build", response_model=BuiltReport)
def build_report(
    req: BuildReportRequest,
    current_user: User = Depends(get_current_user)
):
    """Assembles interactive report with Plotly charts, KPI cards, tables, and filters."""
    if not req.dataset:
        raise HTTPException(status_code=400, detail="Dataset cannot be empty.")

    df = pd.DataFrame(req.dataset)

    if req.template_key:
        try:
            return ReportBuilderService.build_from_template(
                template_key=req.template_key,
                df=df,
                active_filters=req.active_filters
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    if req.definition:
        return ReportBuilderService.build_report(
            definition=req.definition,
            df=df,
            active_filters=req.active_filters
        )

    # If neither provided, fallback to executive overview template
    return ReportBuilderService.build_from_template(
        template_key="executive_overview",
        df=df,
        active_filters=req.active_filters
    )
