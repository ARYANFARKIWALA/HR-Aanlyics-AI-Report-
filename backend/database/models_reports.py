"""SQLAlchemy ORM models for Module 12 - Reports, Versioning, Sharing ACLs, and History."""

import datetime
from sqlalchemy import (
    Column, Integer, Float, String, Boolean, DateTime,
    ForeignKey, Text, Index
)
from sqlalchemy.orm import relationship
from .connection import Base


class SavedReport(Base):
    """Saved enterprise reports with version tracking and ownership."""
    __tablename__ = "saved_reports"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String(64), unique=True, nullable=False, index=True)
    title = Column(String(128), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(64), default="General HR", index=True)
    database_id = Column(String(64), nullable=False, default="sqlite_hr_default")

    sql_query = Column(Text, nullable=False)
    layout_config = Column(Text, nullable=True)  # JSON string of ReportDefinition

    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    author_username = Column(String(64), nullable=True)

    current_version = Column(Integer, default=1)
    is_archived = Column(Boolean, default=False, index=True)
    is_deleted = Column(Boolean, default=False, index=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    versions = relationship("SavedReportVersion", back_populates="report", cascade="all, delete-orphan")
    access_rules = relationship("ReportAccess", back_populates="report", cascade="all, delete-orphan")
    executions = relationship("ReportExecutionRecord", back_populates="report", cascade="all, delete-orphan")


class SavedReportVersion(Base):
    """Immutable version history snapshot for a saved report."""
    __tablename__ = "saved_report_versions"

    id = Column(Integer, primary_key=True, index=True)
    saved_report_id = Column(Integer, ForeignKey("saved_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)

    title = Column(String(128), nullable=False)
    sql_query = Column(Text, nullable=False)
    layout_config = Column(Text, nullable=True)

    modified_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    modified_by_username = Column(String(64), nullable=True)
    change_summary = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    report = relationship("SavedReport", back_populates="versions")

    __table_args__ = (
        Index("idx_report_version", "saved_report_id", "version_number", unique=True),
    )


class ReportAccess(Base):
    """Granular access control list (ACL) for report sharing."""
    __tablename__ = "report_access_rules"

    id = Column(Integer, primary_key=True, index=True)
    saved_report_id = Column(Integer, ForeignKey("saved_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    role_name = Column(String(64), nullable=True, index=True)

    access_level = Column(String(32), default="VIEW", nullable=False)  # VIEW, EDIT, EXPORT, ADMIN
    granted_by = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    report = relationship("SavedReport", back_populates="access_rules")


class ReportExecutionRecord(Base):
    """Execution history specifically linked to a saved report."""
    __tablename__ = "saved_report_executions"

    id = Column(Integer, primary_key=True, index=True)
    saved_report_id = Column(Integer, ForeignKey("saved_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    execution_id = Column(String(64), nullable=False, index=True)
    validation_id = Column(String(64), nullable=False)

    user_id = Column(Integer, nullable=True)
    username = Column(String(64), nullable=True)
    status = Column(String(32), nullable=False)
    row_count = Column(Integer, default=0)
    duration_ms = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    report = relationship("SavedReport", back_populates="executions")
