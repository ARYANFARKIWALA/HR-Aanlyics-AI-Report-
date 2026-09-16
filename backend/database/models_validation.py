"""SQLAlchemy ORM model for Module 7 - SQL Validator & Security Engine Audit."""

import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)

from .connection import Base


class SQLValidationAuditLog(Base):
    """Audit log of all SQL validation decisions and issued validation tokens."""
    __tablename__ = "sql_validation_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    validation_id = Column(String(64), unique=True, nullable=False, index=True)
    database_id = Column(String(64), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    username = Column(String(64), nullable=True)
    user_role = Column(String(32), nullable=True)

    raw_sql = Column(Text, nullable=False)
    sanitized_sql = Column(Text, nullable=False)
    sql_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hash of sanitized SQL

    status = Column(String(32), nullable=False, index=True)  # APPROVED, REJECTED, REQUIRES_APPROVAL
    risk_score = Column(Float, nullable=False, default=0.0)
    risk_level = Column(String(20), nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL

    rules_checked = Column(Text, nullable=True)  # JSON list of checklist items passed
    violations = Column(Text, nullable=True)  # JSON list of violation strings or dicts
    warnings = Column(Text, nullable=True)  # JSON list of warning strings

    expires_at = Column(DateTime, nullable=False, index=True)  # 15 minutes TTL for approved tokens
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_val_lookup", "validation_id", "status", "expires_at"),
    )
