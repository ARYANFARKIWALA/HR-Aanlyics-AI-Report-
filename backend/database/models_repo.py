"""Module 2: Database Models for Existing SQL Repository & SQL Knowledge Management.

Stores SQL report metadata, original queries, normalized queries, versions,
parameters, approval workflows, and categories. Does NOT store actual HR employee data.
"""

import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .connection import Base


class SQLReport(Base):
    """Core enterprise SQL report entry in the repository."""
    __tablename__ = "sql_reports"

    id = Column(Integer, primary_key=True, index=True)
    report_code = Column(String(30), unique=True, nullable=False, index=True)  # e.g., SQLRPT-000001
    organization_id = Column(String(64), default="org_default", nullable=False, index=True)
    database_id = Column(String(64), nullable=False, index=True)  # Module 1 Database Association
    
    report_name = Column(String(150), nullable=False, index=True)
    description = Column(Text, nullable=False)  # Human-authored description
    business_purpose = Column(Text, nullable=True)  # Context for later RAG
    category = Column(String(50), nullable=False, default="Other", index=True)
    
    sql_query = Column(Text, nullable=False)  # Preserved original SQL
    normalized_sql = Column(Text, nullable=False)  # Canonicalized SQL for comparison
    sql_hash = Column(String(64), nullable=False, index=True)  # SHA-256 for duplicate detection

    # Workflow Status: DRAFT, PENDING_REVIEW, VALID, INVALID, APPROVED, ARCHIVED, REJECTED
    status = Column(String(30), default="DRAFT", nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)

    is_valid = Column(Boolean, default=False)
    validation_error = Column(Text, nullable=True)
    validated_at = Column(DateTime, nullable=True)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    metadata_rel = relationship("SQLReportMetadata", back_populates="report", uselist=False, cascade="all, delete-orphan")
    versions = relationship("SQLReportVersion", back_populates="report", cascade="all, delete-orphan", order_by="desc(SQLReportVersion.version_number)")
    parameters = relationship("SQLReportParameter", back_populates="report", cascade="all, delete-orphan")
    approvals = relationship("SQLApproval", back_populates="report", cascade="all, delete-orphan", order_by="desc(SQLApproval.created_at)")
    tags = relationship("SQLReportTag", back_populates="report", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_sql_report_org_db", "organization_id", "database_id"),
        Index("idx_sql_report_status_cat", "status", "category"),
    )


class SQLReportMetadata(Base):
    """Extracted syntactic and structural metadata for an SQL report."""
    __tablename__ = "sql_report_metadata"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("sql_reports.id"), nullable=False, unique=True, index=True)

    table_count = Column(Integer, default=0)
    column_count = Column(Integer, default=0)
    join_count = Column(Integer, default=0)
    cte_count = Column(Integer, default=0)
    subquery_count = Column(Integer, default=0)
    aggregation_count = Column(Integer, default=0)

    uses_effective_dating = Column(Boolean, default=False, index=True)
    uses_security_filter = Column(Boolean, default=False, index=True)
    has_date_logic = Column(Boolean, default=False)
    has_business_logic = Column(Boolean, default=False)

    # Complexity: LOW, MEDIUM, HIGH, VERY_HIGH
    complexity_level = Column(String(20), default="LOW", index=True)
    complexity_score = Column(Float, default=1.0)

    # JSON representations stored as text
    tables_json = Column(Text, default="[]")
    columns_json = Column(Text, default="[]")
    joins_json = Column(Text, default="[]")
    filters_json = Column(Text, default="[]")
    aggregations_json = Column(Text, default="[]")
    date_conditions_json = Column(Text, default="[]")
    effective_dating_details = Column(Text, default="[]")
    security_filters_details = Column(Text, default="[]")
    business_logic_details = Column(Text, default="[]")

    parsed_at = Column(DateTime, default=datetime.datetime.utcnow)

    report = relationship("SQLReport", back_populates="metadata_rel")


class SQLReportParameter(Base):
    """Detected parameter placeholders in SQL queries."""
    __tablename__ = "sql_report_parameters"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("sql_reports.id"), nullable=False, index=True)

    parameter_name = Column(String(100), nullable=False)  # e.g., start_date
    parameter_type = Column(String(50), default="string")  # date, integer, string, list
    required = Column(Boolean, default=True)
    default_value = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    report = relationship("SQLReport", back_populates="parameters")


class SQLReportVersion(Base):
    """Historical versioning for SQL reports."""
    __tablename__ = "sql_report_versions"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("sql_reports.id"), nullable=False, index=True)

    version_number = Column(Integer, nullable=False)
    sql_query = Column(Text, nullable=False)
    normalized_sql = Column(Text, nullable=False)
    change_description = Column(Text, nullable=False)
    changed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    report = relationship("SQLReport", back_populates="versions")


class SQLApproval(Base):
    """Audit trail for review and approval decisions."""
    __tablename__ = "sql_approvals"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("sql_reports.id"), nullable=False, index=True)
    action = Column(String(30), nullable=False)  # APPROVE, REJECT, ARCHIVE, RESTORE
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    report = relationship("SQLReport", back_populates="approvals")


class SQLCategory(Base):
    """Predefined and custom SQL report categories."""
    __tablename__ = "sql_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_predefined = Column(Boolean, default=True)


class Tag(Base):
    """Catalog of reusable descriptive tags."""
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)


class SQLReportTag(Base):
    """Association between SQL reports and tags."""
    __tablename__ = "sql_report_tags"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("sql_reports.id"), nullable=False, index=True)
    tag_id = Column(Integer, ForeignKey("tags.id"), nullable=False, index=True)

    report = relationship("SQLReport", back_populates="tags")
    tag = relationship("Tag")

    __table_args__ = (
        Index("idx_report_tag_unique", "report_id", "tag_id", unique=True),
    )
