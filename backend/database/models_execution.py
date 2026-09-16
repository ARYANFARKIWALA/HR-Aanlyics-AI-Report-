"""SQLAlchemy ORM model for Module 8 - Query Execution Engine Audit."""

import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    ForeignKey, Text, Index
)
from .connection import Base


class QueryExecutionAuditLog(Base):
    """Immutable audit trail for all query executions through Module 8."""
    __tablename__ = "query_execution_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String(64), unique=True, nullable=False, index=True)
    validation_id = Column(String(64), ForeignKey("sql_validation_audit_logs.validation_id", ondelete="SET NULL"), nullable=True, index=True)
    database_id = Column(String(64), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    username = Column(String(64), nullable=True)
    user_role = Column(String(32), nullable=True)

    sql_hash = Column(String(64), nullable=False, index=True)
    status = Column(String(32), nullable=False, index=True)  # SUCCESS, FAILED, TIMEOUT, CANCELLED
    row_count = Column(Integer, default=0)
    execution_time_ms = Column(Float, default=0.0)
    cached = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_exec_lookup", "execution_id", "status"),
    )
