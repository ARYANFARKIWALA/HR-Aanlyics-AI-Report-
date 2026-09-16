"""Core Pydantic schemas for API responses, health, and error envelopes."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "2.0.0"
    database: str = "connected"
    databases_registered: int = 1
    rag_indexed: bool = True


class ReadinessDependencies(BaseModel):
    metadata_database: str
    connection_manager: str
    registered_databases: int
    rag_retriever: str


class ReadinessResponse(BaseModel):
    status: str
    dependencies: ReadinessDependencies


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: dict[str, Any] | None = None
    path: str | None = None


class SuccessResponse(BaseModel):
    status: str = "success"
    message: str


class DataEnvelope(BaseModel, Generic[T]):
    status: str = "success"
    data: T
