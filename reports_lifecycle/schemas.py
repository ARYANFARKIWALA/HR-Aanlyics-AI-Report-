"""Pydantic request/response schemas for Module 12 - Reports Lifecycle."""

from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Literal
from pydantic import BaseModel, Field


class ReportCreateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=128)
    description: Optional[str] = Field(None, max_length=1000)
    category: str = Field(default="General HR", max_length=64)
    database_id: str = Field(default="sqlite_hr_default", max_length=64)
    sql_query: str = Field(..., min_length=5)
    layout_config: Optional[Union[Dict[str, Any], str]] = None


class ReportUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=128)
    description: Optional[str] = None
    category: Optional[str] = None
    database_id: Optional[str] = None
    sql_query: Optional[str] = None
    layout_config: Optional[Union[Dict[str, Any], str]] = None
    change_summary: Optional[str] = Field(default="Report updated", max_length=255)


class ReportDuplicateRequest(BaseModel):
    new_title: Optional[str] = None


class ReportResponse(BaseModel):
    id: int
    report_id: str
    title: str
    description: Optional[str] = None
    category: str
    database_id: str
    sql_query: str
    layout_config: Optional[str] = None
    created_by: Optional[int] = None
    author_username: Optional[str] = None
    current_version: int
    is_archived: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    user_access_level: Optional[str] = None

    class Config:
        from_attributes = True


class ReportVersionResponse(BaseModel):
    id: int
    saved_report_id: int
    version_number: int
    title: str
    sql_query: str
    layout_config: Optional[str] = None
    modified_by: Optional[int] = None
    modified_by_username: Optional[str] = None
    change_summary: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReportAccessCreateRequest(BaseModel):
    user_id: Optional[int] = None
    role_name: Optional[str] = None
    access_level: Literal["VIEW", "EXPORT", "EDIT", "ADMIN"] = "VIEW"


class ReportAccessResponse(BaseModel):
    id: int
    saved_report_id: int
    user_id: Optional[int] = None
    role_name: Optional[str] = None
    access_level: str
    granted_by: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReportExecutionResponse(BaseModel):
    id: int
    saved_report_id: int
    execution_id: str
    validation_id: str
    user_id: Optional[int] = None
    username: Optional[str] = None
    status: str
    row_count: int
    duration_ms: float
    created_at: datetime

    class Config:
        from_attributes = True


class ReportRunRequest(BaseModel):
    database_id: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    limit: Optional[int] = Field(default=None, ge=1, le=10000)
    version_number: Optional[int] = None


class ReportRunResponse(BaseModel):
    report_id: str
    execution_id: str
    validation_id: str
    status: str
    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int
    duration_ms: float
    cached: bool = False
    truncated: bool = False
    error: Optional[str] = None


class ReportExportRequest(BaseModel):
    format: Literal["csv", "excel", "pdf"] = "csv"
    version_number: Optional[int] = None
    include_kpis: bool = True
    include_governance: bool = True
