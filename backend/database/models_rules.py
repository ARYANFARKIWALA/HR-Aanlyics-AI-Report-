"""Module 4: Database Models for HR Business Rule Management.

Defines tables for:
- business_rules
- business_rule_versions
- business_rule_audit
- rule_dependencies
- report_business_rules
- rule_tables
- rule_columns
"""

import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
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


class BusinessRule(Base):
    """Core enterprise business rule definition."""
    __tablename__ = "business_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_code = Column(String(50), unique=True, nullable=False, index=True)  # e.g., BR-EMP-001
    rule_name = Column(String(150), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Categories: EMPLOYEE_STATUS, EFFECTIVE_DATING, SALARY, ATTENDANCE, LEAVE, ATTRITION,
    # DEPARTMENT, LOCATION, JOB, SECURITY, DATA_ACCESS, DATE, CALCULATION, FILTER, AGGREGATION, CUSTOM
    rule_type = Column(String(50), nullable=False, default="FILTER", index=True)

    # Expressions
    rule_expression = Column(Text, nullable=False)  # e.g. employees.status = 'ACTIVE'
    natural_language_rule = Column(Text, nullable=False)  # Plain English business explanation

    # Source: SQL_DETECTED, ADMIN_CREATED, ADMIN_EDITED, IMPORTED, SYSTEM_GENERATED
    source_type = Column(String(40), default="ADMIN_CREATED", nullable=False, index=True)
    source_report_id = Column(String(64), nullable=True)  # Reference to SQLReport.id / code
    source_sql_report = Column(String(150), nullable=True)  # Title / file of source report
    source_sql_expression = Column(Text, nullable=True)  # Original SQL snippet

    # Status: DETECTED, UNDER_REVIEW, APPROVED, REJECTED, DRAFT, ACTIVE, INACTIVE, DEPRECATED
    status = Column(String(30), default="DRAFT", nullable=False, index=True)

    # Priority: LOW, MEDIUM, HIGH, CRITICAL
    priority = Column(String(20), default="MEDIUM", nullable=False, index=True)
    mandatory = Column(Boolean, default=False, nullable=False, index=True)

    # Scope: GLOBAL, DATABASE, TABLE, COLUMN, REPORT, DEPARTMENT, ROLE
    scope = Column(String(30), default="TABLE", nullable=False, index=True)
    database_id = Column(String(64), default="sqlite_hr_default", nullable=False, index=True)
    table_name = Column(String(128), nullable=True, index=True)
    column_name = Column(String(128), nullable=True, index=True)

    # Confidence score: 0.0 - 1.0 (for detected rules)
    confidence_score = Column(Float, default=1.0, nullable=False)

    # Creator & Updater
    created_by = Column(String(64), default="admin")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    updated_by = Column(String(64), nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Approver
    approved_by = Column(String(64), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approval_comment = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Rule validity period
    effective_from = Column(Date, nullable=True)
    effective_to = Column(Date, nullable=True)

    # Versioning
    version = Column(Integer, default=1, nullable=False)
    is_current = Column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    versions = relationship("BusinessRuleVersion", back_populates="rule", cascade="all, delete-orphan")
    audits = relationship("BusinessRuleAudit", back_populates="rule", cascade="all, delete-orphan")
    dependencies = relationship("RuleDependency", foreign_keys="RuleDependency.rule_id", back_populates="rule", cascade="all, delete-orphan")
    tables = relationship("RuleTable", back_populates="rule", cascade="all, delete-orphan")
    columns = relationship("RuleColumn", back_populates="rule", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_rule_db_status", "database_id", "status"),
        Index("idx_rule_type_priority", "rule_type", "priority"),
    )


class BusinessRuleVersion(Base):
    """Immutable version snapshot of a business rule."""
    __tablename__ = "business_rule_versions"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("business_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)

    rule_name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    rule_expression = Column(Text, nullable=False)
    natural_language_rule = Column(Text, nullable=False)
    rule_type = Column(String(50), nullable=False)
    status = Column(String(30), nullable=False)

    changed_by = Column(String(64), default="admin")
    change_reason = Column(Text, nullable=True)
    is_current = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    rule = relationship("BusinessRule", back_populates="versions")

    __table_args__ = (
        Index("idx_rule_ver_num", "rule_id", "version_number", unique=True),
    )


class BusinessRuleAudit(Base):
    """Compliance audit trail for business rule actions."""
    __tablename__ = "business_rule_audit"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("business_rules.id", ondelete="CASCADE"), nullable=False, index=True)

    # Action: CREATE, EDIT, APPROVE, REJECT, ACTIVATE, DEACTIVATE, DELETE, DEPRECATE, VERSION_CREATE
    action = Column(String(30), nullable=False, index=True)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    performed_by = Column(String(64), default="admin")
    performed_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    reason = Column(Text, nullable=True)

    rule = relationship("BusinessRule", back_populates="audits")


class RuleDependency(Base):
    """Dependencies between rules (e.g. Current Salary requires Current Employee)."""
    __tablename__ = "rule_dependencies"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("business_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    depends_on_rule_id = Column(Integer, ForeignKey("business_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    dependency_type = Column(String(30), default="REQUIRES", nullable=False)  # REQUIRES, PRECEDES, EXTENDS
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    rule = relationship("BusinessRule", foreign_keys=[rule_id], back_populates="dependencies")


class ReportBusinessRule(Base):
    """Association linking rules to Module 2 SQL reports."""
    __tablename__ = "report_business_rules"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, nullable=False, index=True)  # SQLReport ID
    rule_id = Column(Integer, ForeignKey("business_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    mandatory = Column(Boolean, default=True)


class RuleTable(Base):
    """Mapping of rules to database tables."""
    __tablename__ = "rule_tables"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("business_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    table_name = Column(String(128), nullable=False, index=True)

    rule = relationship("BusinessRule", back_populates="tables")


class RuleColumn(Base):
    """Mapping of rules to specific database columns."""
    __tablename__ = "rule_columns"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("business_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    table_name = Column(String(128), nullable=False)
    column_name = Column(String(128), nullable=False, index=True)

    rule = relationship("BusinessRule", back_populates="columns")
