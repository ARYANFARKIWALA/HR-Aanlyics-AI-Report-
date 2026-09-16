"""Comprehensive Integration Tests for Phase 14 — Complete End-to-End Integration."""

import uuid

import pytest

from backend.auth.password import hash_password
from backend.database.connection import SessionLocal, init_db
from backend.database.models import User
from backend.database.models_audit import LifecycleAuditLog
from backend.services.workflow_orchestrator import (
    EnterpriseWorkflowOrchestrator,
    WorkflowExecutionError,
)


@pytest.fixture(scope="module")
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def test_admin_user(db_session):
    unique_id = uuid.uuid4().hex[:6]
    unique_user = f"admin_{unique_id}"
    user = User(
        username=unique_user,
        email=f"{unique_user}@example.com",
        full_name="Enterprise Admin",
        hashed_password=hash_password("AdminPass123!"),
        role="SUPER_ADMIN",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_canonical_14_stage_workflow(db_session, test_admin_user):
    """Verify exact 14-stage execution for the canonical scenario:
    'Show monthly employee attrition by department for 2026.'
    """
    orchestrator = EnterpriseWorkflowOrchestrator(db=db_session)
    result = orchestrator.execute_canonical_scenario(
        question="Show monthly employee attrition by department for 2026.",
        database_id="sqlite_hr_default",
        username=test_admin_user.username
    )

    assert result["status"] == "SUCCESS"
    assert result["stages_completed"] == 14
    assert len(result["stages"]) == 14

    expected_stages = [
        "Authenticate User",
        "Identify Selected Database",
        "Retrieve Schema",
        "Retrieve Relevant Approved SQL",
        "Retrieve Attrition Definition",
        "Retrieve Effective-Dating Rules",
        "Generate SQL",
        "Validate SQL",
        "Apply Security",
        "Execute SQL",
        "Calculate Analytics",
        "Create Visualization",
        "Generate Report",
        "Save Audit Record"
    ]

    for idx, stage in enumerate(result["stages"]):
        assert stage["step"] == idx + 1
        assert stage["name"] == expected_stages[idx]

    # Verify generated SQL and execution
    assert result["generated_sql"] is not None
    assert "SELECT" in result["generated_sql"].upper()
    assert result["validation_id"] is not None
    assert result["execution_id"] is not None
    assert result["report_id"] is not None

    # Verify 7 preserved attributes
    preserved = result["preserved_attributes"]
    assert preserved["question"] == "Show monthly employee attrition by department for 2026."
    assert preserved["sql"] == result["generated_sql"]
    assert preserved["database"] == "sqlite_hr_default"
    assert isinstance(preserved["knowledge_sources"], (list, dict))
    assert preserved["timestamp"] is not None
    assert preserved["user"] == test_admin_user.username
    assert preserved["report_version"] == 1

    # Verify audit record persisted
    audit_entry = db_session.query(LifecycleAuditLog).filter(
        LifecycleAuditLog.event_type == "END_TO_END_INTEGRATION_COMPLETED",
        LifecycleAuditLog.username == test_admin_user.username
    ).order_by(LifecycleAuditLog.id.desc()).first()
    assert audit_entry is not None
    assert audit_entry.status == "SUCCESS"


def test_workflow_security_boundary_inactive_user(db_session):
    """Verify that an inactive user cannot initiate the workflow."""
    unique_id = uuid.uuid4().hex[:6]
    inactive_user = User(
        username=f"inactive_{unique_id}",
        email=f"inactive_{unique_id}@example.com",
        full_name="Inactive Employee",
        hashed_password=hash_password("Pass123!"),
        role="ANALYST",
        is_active=False
    )
    db_session.add(inactive_user)
    db_session.commit()

    orchestrator = EnterpriseWorkflowOrchestrator(db=db_session)
    with pytest.raises(WorkflowExecutionError) as exc:
        orchestrator.execute_canonical_scenario(
            question="Show headcount by department",
            username=inactive_user.username
        )
    assert "Step 1 Failed" in str(exc.value)


def test_workflow_security_boundary_unauthorized_database(db_session, test_admin_user):
    """Verify that targeting an invalid or nonexistent database fails early at step 2 or 3."""
    orchestrator = EnterpriseWorkflowOrchestrator(db=db_session)
    with pytest.raises(WorkflowExecutionError):
        orchestrator.execute_canonical_scenario(
            question="Show headcount",
            database_id="non_existent_unauthorized_db",
            username=test_admin_user.username
        )
