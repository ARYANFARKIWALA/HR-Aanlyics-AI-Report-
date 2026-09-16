"""Enterprise Audit Service recording 13 lifecycle events (Module 13)."""

import datetime
import json
from typing import Any

from sqlalchemy.orm import Session

from backend.audit.sanitizer import AuditDataSanitizer
from backend.database.models_audit import LifecycleAuditLog


class EnterpriseAuditService:
    """Records all 13 required platform lifecycle events with zero credential leakage."""

    EVENT_USER_LOGIN = "USER_LOGIN"
    EVENT_DATABASE_SELECTION = "DATABASE_SELECTION"
    EVENT_SQL_UPLOAD = "SQL_UPLOAD"
    EVENT_BUSINESS_RULE_CHANGE = "BUSINESS_RULE_CHANGE"
    EVENT_AI_QUESTION = "AI_QUESTION"
    EVENT_RETRIEVED_KNOWLEDGE = "RETRIEVED_KNOWLEDGE"
    EVENT_GENERATED_SQL = "GENERATED_SQL"
    EVENT_VALIDATION_RESULT = "VALIDATION_RESULT"
    EVENT_QUERY_EXECUTION = "QUERY_EXECUTION"
    EVENT_REPORT_CREATION = "REPORT_CREATION"
    EVENT_REPORT_DOWNLOAD = "REPORT_DOWNLOAD"
    EVENT_PERMISSION_CHANGE = "PERMISSION_CHANGE"
    EVENT_ERROR = "ERROR"

    def __init__(self, db: Session):
        self.db = db

    def log_event(
        self,
        event_type: str,
        username: str = "system",
        user_role: str = "anonymous",
        database_id: str | None = None,
        details: dict[str, Any] | None = None,
        status: str = "SUCCESS",
        execution_time_ms: float = 0.0,
        error_message: str | None = None,
        user_id: int | None = None,
        ip_address: str = "127.0.0.1"
    ) -> LifecycleAuditLog:
        """Sanitizes and persists lifecycle audit log."""
        clean_details = AuditDataSanitizer.sanitize(details or {})
        clean_error = AuditDataSanitizer.sanitize(error_message) if error_message else None

        entry = LifecycleAuditLog(
            event_type=event_type,
            user_id=user_id,
            username=username,
            user_role=user_role,
            database_id=database_id,
            status=status,
            execution_time_ms=execution_time_ms,
            details=json.dumps(clean_details),
            error_message=clean_error,
            ip_address=ip_address,
            created_at=datetime.datetime.now(datetime.UTC)
        )
        try:
            self.db.add(entry)
            self.db.commit()
            self.db.refresh(entry)
            return entry
        except Exception:
            self.db.rollback()
            return entry

    # 1. User login
    def log_user_login(self, username: str, success: bool, ip: str = "127.0.0.1", user_role: str = "user"):
        return self.log_event(
            event_type=self.EVENT_USER_LOGIN,
            username=username,
            user_role=user_role,
            status="SUCCESS" if success else "BLOCKED",
            ip_address=ip,
            details={"login_successful": success}
        )

    # 2. Database selection
    def log_database_selection(self, username: str, database_id: str, user_role: str = "user"):
        return self.log_event(
            event_type=self.EVENT_DATABASE_SELECTION,
            username=username,
            user_role=user_role,
            database_id=database_id,
            details={"selected_database_id": database_id}
        )

    # 3. SQL upload
    def log_sql_upload(self, username: str, report_id: str, title: str, database_id: str, user_role: str = "user"):
        return self.log_event(
            event_type=self.EVENT_SQL_UPLOAD,
            username=username,
            user_role=user_role,
            database_id=database_id,
            details={"report_id": report_id, "title": title}
        )

    # 4. Business rule changes
    def log_business_rule_change(self, username: str, rule_id: int, action: str, rule_name: str, user_role: str = "user"):
        return self.log_event(
            event_type=self.EVENT_BUSINESS_RULE_CHANGE,
            username=username,
            user_role=user_role,
            details={"rule_id": rule_id, "action": action, "rule_name": rule_name}
        )

    # 5. AI question
    def log_ai_question(self, username: str, question: str, database_id: str, user_role: str = "user"):
        return self.log_event(
            event_type=self.EVENT_AI_QUESTION,
            username=username,
            user_role=user_role,
            database_id=database_id,
            details={"natural_language_question": question}
        )

    # 6. Retrieved knowledge
    def log_retrieved_knowledge(self, username: str, query: str, chunk_count: int, latency_ms: float, user_role: str = "user"):
        return self.log_event(
            event_type=self.EVENT_RETRIEVED_KNOWLEDGE,
            username=username,
            user_role=user_role,
            execution_time_ms=latency_ms,
            details={"query": query, "chunks_retrieved": chunk_count}
        )

    # 7. Generated SQL
    def log_generated_sql(self, username: str, query: str, dialect: str, sql: str, user_role: str = "user"):
        return self.log_event(
            event_type=self.EVENT_GENERATED_SQL,
            username=username,
            user_role=user_role,
            details={"query": query, "dialect": dialect, "generated_sql": sql}
        )

    # 8. Validation result
    def log_validation_result(self, username: str, validation_id: str, status: str, risk_score: float, database_id: str, user_role: str = "user"):
        return self.log_event(
            event_type=self.EVENT_VALIDATION_RESULT,
            username=username,
            user_role=user_role,
            database_id=database_id,
            status=status,
            details={"validation_id": validation_id, "risk_score": risk_score}
        )

    # 9. Query execution
    def log_query_execution(self, username: str, execution_id: str, status: str, row_count: int, time_ms: float, database_id: str, user_role: str = "user"):
        return self.log_event(
            event_type=self.EVENT_QUERY_EXECUTION,
            username=username,
            user_role=user_role,
            database_id=database_id,
            status=status,
            execution_time_ms=time_ms,
            details={"execution_id": execution_id, "row_count": row_count}
        )

    # 10. Report creation
    def log_report_creation(self, username: str, report_id: str, title: str, database_id: str, user_role: str = "user"):
        return self.log_event(
            event_type=self.EVENT_REPORT_CREATION,
            username=username,
            user_role=user_role,
            database_id=database_id,
            details={"report_id": report_id, "title": title}
        )

    # 11. Report download
    def log_report_download(self, username: str, report_id: str, format_type: str, user_role: str = "user"):
        return self.log_event(
            event_type=self.EVENT_REPORT_DOWNLOAD,
            username=username,
            user_role=user_role,
            details={"report_id": report_id, "format": format_type}
        )

    # 12. Permission changes
    def log_permission_change(self, username: str, target_user: str, role_assigned: str, user_role: str = "admin"):
        return self.log_event(
            event_type=self.EVENT_PERMISSION_CHANGE,
            username=username,
            user_role=user_role,
            details={"target_user": target_user, "role_assigned": role_assigned}
        )

    # 13. Errors
    def log_error(self, username: str, error_type: str, message: str, database_id: str | None = None, user_role: str = "user"):
        return self.log_event(
            event_type=self.EVENT_ERROR,
            username=username,
            user_role=user_role,
            database_id=database_id,
            status="ERROR",
            error_message=message,
            details={"error_type": error_type}
        )
