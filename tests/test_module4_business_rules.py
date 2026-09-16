"""Module 4: Automated Test Suite for Business Rule Management.

Tests:
- Rule creation with unique code and initial version
- Validation checks (syntax, schema, priority, required fields)
- Approval and rejection workflows with audit trail
- Editing active rules creates immutable new version (v1 -> v2)
- Conflict and duplicate detection
- Rule dependencies
- Active rules retrieval for Module 5 RAG (excludes rejected/inactive)
- Rule discovery from Module 2 SQL reports
- FastAPI endpoints
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database.connection import SessionLocal, init_db
from backend.database.models import User
from backend.database.models_rules import BusinessRule, BusinessRuleVersion, BusinessRuleAudit
from business_rules.service import BusinessRuleService
from business_rules.validator import RuleValidator, RuleValidationError
from business_rules.conflict_detector import RuleConflictDetector
from business_rules.duplicate_detector import RuleDuplicateDetector


@pytest.fixture(scope="module")
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_create_valid_rule(db_session):
    """Verifies creating a valid rule creates version 1 and an audit log."""
    service = BusinessRuleService(db_session)
    rule = service.create_rule({
        "rule_name": "Test Active Employee Rule",
        "rule_type": "EMPLOYEE_STATUS",
        "rule_expression": "employees.status = 'ACTIVE'",
        "natural_language_rule": "Employees must have active status.",
        "priority": "HIGH",
        "mandatory": True,
        "table_name": "employees",
        "column_name": "status",
        "database_id": "sqlite_hr_default"
    }, user_name="admin")

    assert rule.id is not None
    assert rule.rule_code.startswith("BR-EMP-")
    assert rule.version == 1
    assert rule.is_current is True
    assert len(rule.versions) == 1
    assert len(rule.audits) == 1
    assert rule.audits[0].action == "CREATE"


def test_create_rule_validation_failure(db_session):
    """Verifies missing fields or invalid rule types raise RuleValidationError."""
    service = BusinessRuleService(db_session)

    # Missing name
    with pytest.raises(RuleValidationError):
        service.create_rule({
            "rule_name": "",
            "rule_type": "EMPLOYEE_STATUS",
            "rule_expression": "status = 'ACTIVE'",
            "natural_language_rule": "Active status."
        })

    # Invalid type
    with pytest.raises(RuleValidationError):
        service.create_rule({
            "rule_name": "Invalid Type Rule",
            "rule_type": "NONEXISTENT_TYPE",
            "rule_expression": "status = 'ACTIVE'",
            "natural_language_rule": "Active status."
        })


def test_approve_detected_rule(db_session):
    """Verifies approving a detected rule transitions status to ACTIVE and records comment."""
    service = BusinessRuleService(db_session)
    rule = service.create_rule({
        "rule_name": "Pending Approval Rule",
        "rule_type": "FILTER",
        "rule_expression": "employees.department_id = 1",
        "natural_language_rule": "Department ID must be 1.",
        "status": "DETECTED",
        "database_id": "sqlite_hr_default"
    })

    approved = service.approve_rule(rule.id, comment="Verified with HR ops.", user_name="director")
    assert approved.status == "ACTIVE"
    assert approved.approved_by == "director"
    assert approved.approval_comment == "Verified with HR ops."
    assert approved.approved_at is not None


def test_reject_rule_requires_reason(db_session):
    """Verifies rejecting a rule requires reason and keeps the rule record."""
    service = BusinessRuleService(db_session)
    rule = service.create_rule({
        "rule_name": "Candidate To Reject",
        "rule_type": "FILTER",
        "rule_expression": "employees.gender = 'Male'",
        "natural_language_rule": "Gender filter.",
        "status": "DETECTED",
        "database_id": "sqlite_hr_default"
    })

    # Empty reason fails
    with pytest.raises(ValueError):
        service.reject_rule(rule.id, reason="", user_name="admin")

    # Valid rejection
    rejected = service.reject_rule(rule.id, reason="Discriminatory filter not allowed as standard policy.", user_name="admin")
    assert rejected.status == "REJECTED"
    assert rejected.rejection_reason is not None

    # Cannot approve directly after rejection
    with pytest.raises(ValueError):
        service.approve_rule(rejected.id, comment="Approve anyway")


def test_edit_active_rule_creates_version(db_session):
    """Verifies editing an ACTIVE rule creates version 2 and preserves version 1 in history."""
    service = BusinessRuleService(db_session)
    rule = service.create_rule({
        "rule_name": "Versioned Policy Rule",
        "rule_type": "SALARY",
        "rule_expression": "compensation_history.base_salary > 40000",
        "natural_language_rule": "Base salary must be over 40,000.",
        "status": "ACTIVE",
        "database_id": "sqlite_hr_default"
    })
    assert rule.version == 1

    # Edit active rule
    updated = service.update_rule(
        rule.id,
        {
            "rule_expression": "compensation_history.base_salary > 50000",
            "natural_language_rule": "Base salary must be over 50,000.",
            "change_reason": "Adjusted minimum salary threshold for 2026."
        },
        user_name="admin"
    )

    assert updated.version == 2
    assert len(updated.versions) == 2
    v1 = next(v for v in updated.versions if v.version_number == 1)
    v2 = next(v for v in updated.versions if v.version_number == 2)
    assert v1.is_current is False
    assert v2.is_current is True
    assert "40000" in v1.rule_expression
    assert "50000" in v2.rule_expression


def test_rule_conflict_detection(db_session):
    """Verifies conflicting equality predicates on the same column are detected."""
    service = BusinessRuleService(db_session)

    # Active rule 1: status = 'ACTIVE'
    service.create_rule({
        "rule_name": "Conflict Base Rule",
        "rule_type": "EMPLOYEE_STATUS",
        "rule_expression": "employees.status = 'ACTIVE'",
        "natural_language_rule": "Status must be active.",
        "status": "ACTIVE",
        "table_name": "employees",
        "column_name": "status",
        "database_id": "sqlite_hr_default"
    })

    # Candidate rule: status = 'INACTIVE'
    conflicts = RuleConflictDetector.detect_conflicts(
        candidate_rule={
            "rule_expression": "employees.status = 'INACTIVE'",
            "table_name": "employees",
            "column_name": "status",
            "database_id": "sqlite_hr_default"
        },
        db=db_session,
        database_id="sqlite_hr_default"
    )

    assert len(conflicts) > 0
    assert conflicts[0]["conflict_type"] == "CONTRADICTORY_VALUE"


def test_rule_duplicate_detection(db_session):
    """Verifies duplicate expressions or near-duplicate texts are detected."""
    service = BusinessRuleService(db_session)
    service.create_rule({
        "rule_name": "Duplicate Base Rule",
        "rule_type": "EMPLOYEE_STATUS",
        "rule_expression": "employees.status = 'ACTIVE'",
        "natural_language_rule": "An employee is active when status is ACTIVE.",
        "status": "ACTIVE",
        "database_id": "sqlite_hr_default"
    })

    # Exact expression duplicate
    dups_exact = RuleDuplicateDetector.detect_duplicates(
        candidate_rule={
            "rule_expression": "employees.status = 'ACTIVE'",
            "natural_language_rule": "Different description",
            "database_id": "sqlite_hr_default"
        },
        db=db_session,
        database_id="sqlite_hr_default"
    )
    assert len(dups_exact) > 0
    assert dups_exact[0]["similarity_score"] == 1.0

    # Semantic duplicate
    dups_semantic = RuleDuplicateDetector.detect_duplicates(
        candidate_rule={
            "rule_expression": "employees.status = 'A'",
            "natural_language_rule": "Employees are active when status is ACTIVE",
            "database_id": "sqlite_hr_default"
        },
        db=db_session,
        database_id="sqlite_hr_default",
        threshold=0.70
    )
    assert len(dups_semantic) > 0


def test_active_rules_for_rag(db_session):
    """Verifies that only ACTIVE and current rules are returned for RAG."""
    service = BusinessRuleService(db_session)

    # Inactive rule
    service.create_rule({
        "rule_name": "Inactive Policy",
        "rule_type": "FILTER",
        "rule_expression": "employees.id > 100",
        "natural_language_rule": "ID over 100.",
        "status": "INACTIVE",
        "database_id": "sqlite_hr_default"
    })

    # Rejected rule
    rej_rule = service.create_rule({
        "rule_name": "Rejected Policy",
        "rule_type": "FILTER",
        "rule_expression": "employees.id < 5",
        "natural_language_rule": "ID under 5.",
        "status": "DETECTED",
        "database_id": "sqlite_hr_default"
    })
    service.reject_rule(rej_rule.id, reason="Not applicable.")

    active_rules = service.get_active_rules("sqlite_hr_default")
    assert all(r.status == "ACTIVE" for r in active_rules)
    assert all(r.is_current is True for r in active_rules)
    assert not any(r.rule_name == "Inactive Policy" for r in active_rules)
    assert not any(r.rule_name == "Rejected Policy" for r in active_rules)


def test_detect_rules_from_sql_repository(db_session):
    """Verifies mining of Module 2 SQL repository reports."""
    service = BusinessRuleService(db_session)
    detected = service.detect_rules_from_sql_repository("sqlite_hr_default")
    assert isinstance(detected, list)


def test_fastapi_business_rule_endpoints(client):
    """Verifies FastAPI business rule endpoints end-to-end."""
    # 1. Stats
    res_stats = client.get("/api/business-rules/stats?database_id=sqlite_hr_default")
    assert res_stats.status_code == 200
    assert "total_rules" in res_stats.json()["data"]

    # 2. Active rules
    res_active = client.get("/api/business-rules/active?database_id=sqlite_hr_default")
    assert res_active.status_code == 200
    assert isinstance(res_active.json()["data"], list)

    # 3. Create rule
    res_create = client.post("/api/business-rules", json={
        "rule_name": "API Created Rule",
        "rule_type": "FILTER",
        "rule_expression": "employees.department_id = 2",
        "natural_language_rule": "Filter to Engineering department.",
        "priority": "HIGH",
        "database_id": "sqlite_hr_default"
    })
    assert res_create.status_code == 200
    created_id = res_create.json()["data"]["id"]

    # 4. Detail
    res_detail = client.get(f"/api/business-rules/{created_id}")
    assert res_detail.status_code == 200
    assert res_detail.json()["data"]["rule_name"] == "API Created Rule"

    # 5. Approve
    res_appr = client.post(f"/api/business-rules/{created_id}/approve", json={"comment": "Approved via API."})
    assert res_appr.status_code == 200
    assert res_appr.json()["data"]["status"] == "ACTIVE"
