"""Unit and Integration Tests for Project Foundation Architecture."""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.core import (
    setup_logging,
    get_logger,
    AppException,
    NotFoundError,
    SecurityError,
    settings,
    EnvironmentType
)
from backend.models import User, Department, Employee
from backend.schemas import HealthResponse, ReadinessResponse, ErrorResponse
from modules.database import connection_manager
from modules.sql_validator import SQLValidatorService
from modules.query_engine import QueryExecutionService
from modules.reports import ReportLifecycleService
from frontend.components import render_header, render_sidebar


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_backend_core_logging():
    """Test 1: Structured logging setup and logger retrieval."""
    setup_logging("DEBUG")
    logger = get_logger("test.foundation")
    assert logger is not None
    assert logger.name == "test.foundation"


def test_backend_core_errors():
    """Test 2: Standardized application exceptions and status codes."""
    exc_base = AppException("Test base", status_code=500, details={"ctx": 1})
    assert exc_base.status_code == 500
    assert exc_base.details["ctx"] == 1

    exc_nf = NotFoundError("Missing item")
    assert exc_nf.status_code == 404

    exc_sec = SecurityError("Blocked access")
    assert exc_sec.status_code == 403


def test_backend_core_config():
    """Test 3: Typed settings loaded and accessible through backend.core."""
    assert settings.app_name == "HR-Analytics-AI-Report-Builder"
    assert settings.api_port == 8000
    assert settings.frontend_port == 8501
    assert isinstance(settings.environment, str)


def test_backend_models_exports():
    """Test 4: Database models cleanly exported via backend.models."""
    assert User.__tablename__ == "users"
    assert Department.__tablename__ == "departments"
    assert Employee.__tablename__ == "employees"


def test_backend_schemas_models():
    """Test 5: Pydantic schemas validate correctly."""
    h = HealthResponse(status="healthy", version="2.0.0", database="connected")
    assert h.status == "healthy"
    assert h.version == "2.0.0"

    err = ErrorResponse(error="TestErr", message="Something broke")
    assert err.error == "TestErr"


def test_modules_package_exports():
    """Test 6: Modular architecture packages correctly expose subsystem capabilities."""
    assert connection_manager is not None
    assert SQLValidatorService is not None
    assert QueryExecutionService is not None
    assert ReportLifecycleService is not None


def test_api_health_and_readiness_endpoints(client):
    """Test 7: API health and readiness endpoints adhere to response contracts."""
    resp_health = client.get("/health")
    assert resp_health.status_code == 200
    data_h = resp_health.json()
    assert data_h["status"] == "healthy"
    assert data_h["version"] == "2.0.0"

    resp_ready = client.get("/ready")
    assert resp_ready.status_code == 200
    data_r = resp_ready.json()
    assert data_r["status"] == "ready"
    assert "dependencies" in data_r
    assert data_r["dependencies"]["metadata_database"] == "ok"
