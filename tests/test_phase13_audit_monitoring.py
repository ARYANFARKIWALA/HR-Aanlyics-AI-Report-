"""Comprehensive Unit and Integration Tests for Phase 13 — Audit Logging & Monitoring."""

import pytest
import json
from backend.database.connection import SessionLocal, init_db
from backend.audit.service import EnterpriseAuditService
from backend.audit.sanitizer import AuditDataSanitizer
from backend.audit.metrics_service import AdminMonitoringService
from backend.database.models_audit import LifecycleAuditLog


@pytest.fixture(scope="module")
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def test_audit_records_all_13_lifecycle_events(db_session):
    """Verify logging all 13 required platform lifecycle events."""
    audit_svc = EnterpriseAuditService(db=db_session)
    username = "test_audit_user"

    # 1. User login
    e1 = audit_svc.log_user_login(username=username, success=True)
    assert e1.event_type == EnterpriseAuditService.EVENT_USER_LOGIN

    # 2. Database selection
    e2 = audit_svc.log_database_selection(username=username, database_id="sqlite_hr_default")
    assert e2.event_type == EnterpriseAuditService.EVENT_DATABASE_SELECTION

    # 3. SQL upload
    e3 = audit_svc.log_sql_upload(username=username, report_id="rep_test_01", title="Test Upload", database_id="sqlite_hr_default")
    assert e3.event_type == EnterpriseAuditService.EVENT_SQL_UPLOAD

    # 4. Business rule change
    e4 = audit_svc.log_business_rule_change(username=username, rule_id=101, action="APPROVED", rule_name="Active Status Policy")
    assert e4.event_type == EnterpriseAuditService.EVENT_BUSINESS_RULE_CHANGE

    # 5. AI question
    e5 = audit_svc.log_ai_question(username=username, question="Show monthly employee attrition by department for 2026.", database_id="sqlite_hr_default")
    assert e5.event_type == EnterpriseAuditService.EVENT_AI_QUESTION

    # 6. Retrieved knowledge
    e6 = audit_svc.log_retrieved_knowledge(username=username, query="Show attrition", chunk_count=4, latency_ms=12.5)
    assert e6.event_type == EnterpriseAuditService.EVENT_RETRIEVED_KNOWLEDGE

    # 7. Generated SQL
    e7 = audit_svc.log_generated_sql(username=username, query="Show attrition", dialect="sqlite", sql="SELECT * FROM employees")
    assert e7.event_type == EnterpriseAuditService.EVENT_GENERATED_SQL

    # 8. Validation result
    e8 = audit_svc.log_validation_result(username=username, validation_id="val_test_99", status="APPROVED", risk_score=15.0, database_id="sqlite_hr_default")
    assert e8.event_type == EnterpriseAuditService.EVENT_VALIDATION_RESULT

    # 9. Query execution
    e9 = audit_svc.log_query_execution(username=username, execution_id="exec_test_99", status="SUCCESS", row_count=25, time_ms=35.2, database_id="sqlite_hr_default")
    assert e9.event_type == EnterpriseAuditService.EVENT_QUERY_EXECUTION

    # 10. Report creation
    e10 = audit_svc.log_report_creation(username=username, report_id="rep_test_99", title="Monthly Attrition Report", database_id="sqlite_hr_default")
    assert e10.event_type == EnterpriseAuditService.EVENT_REPORT_CREATION

    # 11. Report download
    e11 = audit_svc.log_report_download(username=username, report_id="rep_test_99", format_type="PDF")
    assert e11.event_type == EnterpriseAuditService.EVENT_REPORT_DOWNLOAD

    # 12. Permission changes
    e12 = audit_svc.log_permission_change(username=username, target_user="analyst_bob", role_assigned="HR_MANAGER")
    assert e12.event_type == EnterpriseAuditService.EVENT_PERMISSION_CHANGE

    # 13. Errors
    e13 = audit_svc.log_error(username=username, error_type="SYNTAX_ERROR", message="Unexpected token near SELECT")
    assert e13.event_type == EnterpriseAuditService.EVENT_ERROR


def test_zero_credential_leakage(db_session):
    """Verify that passwords, tokens, connection strings, and sensitive HR attributes are scrubbed."""
    audit_svc = EnterpriseAuditService(db=db_session)
    sensitive_payload = {
        "password": "SuperSecretPassword123!",
        "hashed_password": "4395ef87446936cfa4a3348c183207d4d47f566de1164625034c9f88ad00ca22",
        "api_key": "sk-secret-token-key-9999",
        "ssn": "000-12-3456",
        "connection_url": "postgresql://dbadmin:UltraSecretPassword@db.corp.local:5432/hr",
        "bank_account_number": "123456789012"
    }

    entry = audit_svc.log_event(
        event_type="TEST_SECURITY_SCRUB",
        username="sec_user",
        details=sensitive_payload,
        error_message="Failed connecting to postgresql://dbadmin:UltraSecretPassword@db.corp.local:5432/hr"
    )

    persisted_details = json.loads(entry.details)
    assert persisted_details["password"] == "[REDACTED]"
    assert persisted_details["hashed_password"] == "[REDACTED]"
    assert persisted_details["api_key"] == "[REDACTED]"
    assert persisted_details["bank_account_number"] == "[REDACTED]"
    assert "UltraSecretPassword" not in entry.error_message
    assert "***:***@" in entry.error_message


def test_admin_monitoring_metrics(db_session):
    """Test telemetry metrics calculation for the Admin Dashboard."""
    monitoring_svc = AdminMonitoringService(db=db_session)
    metrics = monitoring_svc.get_monitoring_summary()

    assert "ai_requests" in metrics
    assert "sql_success_rate" in metrics
    assert "sql_rejection_rate" in metrics
    assert "average_response_time_ms" in metrics
    assert "query_execution_time_ms" in metrics
    assert "rag_retrieval_performance_ms" in metrics
    assert "failed_requests" in metrics
    assert "system_health" in metrics

    assert metrics["sql_success_rate"] >= 0.0
    assert metrics["sql_rejection_rate"] >= 0.0
