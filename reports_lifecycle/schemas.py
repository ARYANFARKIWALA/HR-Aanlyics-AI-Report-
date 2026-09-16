"""Pydantic request/response schemas for Module 12 - Reports Lifecycle."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ReportCreateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=128)
    description: str | None = Field(None, max_length=1000)
    category: str = Field(default="General HR", max_length=64)
    database_id: str = Field(default="sqlite_hr_default", max_length=64)
    sql_query: str = Field(..., min_length=5)
    layout_config: dict[str, Any] | str | None = None


class ReportUpdateRequest(BaseModel):
    title: str | None = Field(None, min_length=2, max_length=128)
    description: str | None = None
    category: str | None = None
    database_id: str | None = None
    sql_query: str | None = None
    layout_config: dict[str, Any] | str | None = None
    change_summary: str | None = Field(default="Report updated", max_length=255)


class ReportDuplicateRequest(BaseModel):
    new_title: str | None = None


class ReportResponse(BaseModel):
    id: int
    report_id: str
    title: str
    description: str | None = None
    category: str
    database_id: str
    sql_query: str
    layout_config: str | None = None
    created_by: int | None = None
    author_username: str | None = None
    current_version: int
    is_archived: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    user_access_level: str | None = None

    class Config:
        from_attributes = True


class ReportVersionResponse(BaseModel):
    id: int
    saved_report_id: int
    version_number: int
    title: str
    sql_query: str
    layout_config: str | None = None
    modified_by: int | None = None
    modified_by_username: str | None = None
    change_summary: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReportAccessCreateRequest(BaseModel):
    user_id: int | None = None
    role_name: str | None = None
    access_level: Literal["VIEW", "EXPORT", "EDIT", "ADMIN"] = "VIEW"


class ReportAccessResponse(BaseModel):
    id: int
    saved_report_id: int
    user_id: int | None = None
    role_name: str | None = None
    access_level: str
    granted_by: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReportExecutionResponse(BaseModel):
    id: int
    saved_report_id: int
    execution_id: str
    validation_id: str
    user_id: int | None = None
    username: str | None = None
    status: str
    row_count: int
    duration_ms: float
    created_at: datetime

    class Config:
        from_attributes = True


class ReportRunRequest(BaseModel):
    database_id: str | None = None
    parameters: dict[str, Any] | None = None
    limit: int | None = Field(default=None, ge=1, le=10000)
    version_number: int | None = None


class ReportRunResponse(BaseModel):
    report_id: str
    execution_id: str
    validation_id: str
    status: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    duration_ms: float
    cached: bool = False
    truncated: bool = False
    error: str | None = None


class ReportExportRequest(BaseModel):
    format: Literal["csv", "excel", "pdf"] = "csv"
    version_number: int | None = None
    include_kpis: bool = True
    include_governance: bool = True
