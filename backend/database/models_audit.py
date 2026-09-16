"""SQLAlchemy ORM Data Models for Lifecycle Audit Logging (Module 13)."""

import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, Index
)
from .connection import Base


class LifecycleAuditLog(Base):
    """Immutable enterprise audit trail recording all 13 required platform lifecycle events."""
    __tablename__ = "lifecycle_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    # Event types:
    # USER_LOGIN, DATABASE_SELECTION, SQL_UPLOAD, BUSINESS_RULE_CHANGE,
    # AI_QUESTION, RETRIEVED_KNOWLEDGE, GENERATED_SQL, VALIDATION_RESULT,
    # QUERY_EXECUTION, REPORT_CREATION, REPORT_DOWNLOAD, PERMISSION_CHANGE, ERROR

    user_id = Column(Integer, nullable=True, index=True)
    username = Column(String(64), default="system", index=True)
    user_role = Column(String(32), default="anonymous")
    database_id = Column(String(64), nullable=True, index=True)
    status = Column(String(20), default="SUCCESS")  # SUCCESS, BLOCKED, ERROR, REJECTED
    execution_time_ms = Column(Float, default=0.0)
    details = Column(Text, nullable=True)  # Sanitized JSON details
    error_message = Column(Text, nullable=True)
    ip_address = Column(String(45), default="127.0.0.1")
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC), index=True)

    __table_args__ = (
        Index("idx_audit_event_time", "event_type", "created_at"),
        Index("idx_audit_user_time", "username", "created_at"),
    )
