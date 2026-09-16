"""Pydantic schemas for Module 8 - Query Execution Engine."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class QueryColumnMeta(BaseModel):
    name: str
    type: str = "string"
    nullable: bool = True


class ExecuteQueryRequest(BaseModel):
    validation_id: str = Field(..., description="Cryptographic approval token issued strictly by Module 7")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Safe parameterized values")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=100, ge=1, le=1000)
    bypass_cache: bool = False


class QueryExecutionResponse(BaseModel):
    execution_id: str
    query_id: str = ""  # Canonical standardized alias
    validation_id: str
    database_id: str
    status: str  # SUCCESS, FAILED, TIMEOUT, CANCELLED
    columns: List[str] = []
    column_metadata: List[QueryColumnMeta] = []
    rows: List[Dict[str, Any]] = []
    row_count: int = 0
    total_rows: int = 0
    page: int = 1
    page_size: int = 100
    execution_time_ms: float = 0.0
    execution_time: float = 0.0  # In seconds for standard format
    cached: bool = False
    sql_hash: str
    executed_at: str
    error_message: Optional[str] = None

    def to_standard_dict(self) -> Dict[str, Any]:
        """Returns the canonical standardized result payload required by Phase 8."""
        return {
            "columns": self.columns,
            "rows": self.rows,
            "row_count": self.row_count,
            "execution_time": self.execution_time or round(self.execution_time_ms / 1000.0, 4),
            "query_id": self.query_id or self.execution_id
        }
