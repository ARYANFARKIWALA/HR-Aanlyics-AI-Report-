"""Module 3: Database Models for HR Database Schema & Business Metadata Intelligence.

Stores discovered database schemas, tables, views, columns, relationships,
indexes, constraints, snapshots, schema drift/changes, and SQL usage intelligence.
Does NOT store actual HR employee data.
"""

import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    ForeignKey, Text, Index, JSON
)
from sqlalchemy.orm import relationship
from .connection import Base


class SchemaTable(Base):
    """Metadata for a discovered database table or view."""
    __tablename__ = "schema_tables"

    id = Column(Integer, primary_key=True, index=True)
    database_id = Column(String(64), nullable=False, index=True)  # Module 1 DB Connection ID
    schema_name = Column(String(64), default="main", nullable=False)
    table_name = Column(String(128), nullable=False, index=True)
    table_type = Column(String(20), default="TABLE", nullable=False)  # TABLE or VIEW
    row_count_approx = Column(Integer, default=0)

    # Human & Semantic Metadata
    business_name = Column(String(150), nullable=True)
    description = Column(Text, nullable=True)
    business_entity = Column(String(50), default="OTHER", index=True)
    # e.g., EMPLOYEE, DEPARTMENT, JOB_POSITION, COMPENSATION, PAYROLL, PERFORMANCE,
    # LEAVE_ATTENDANCE, BENEFITS, RECRUITMENT, ORGANIZATION_UNIT, LOCATION, OTHER

    importance_score = Column(Float, default=50.0)  # 0.0 - 100.0 computed from SQL usage & schema centrality
    importance_level = Column(String(20), default="MEDIUM", index=True)  # CRITICAL, HIGH, MEDIUM, LOW
    uses_effective_dating = Column(Boolean, default=False, index=True)

    # Review & Governance Workflow: AUTO_DISCOVERED, PENDING_REVIEW, VERIFIED
    status = Column(String(30), default="AUTO_DISCOVERED", nullable=False, index=True)
    verified_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    columns = relationship("SchemaColumn", back_populates="table", cascade="all, delete-orphan", order_by="SchemaColumn.ordinal_position")
    indexes = relationship("SchemaIndex", back_populates="table", cascade="all, delete-orphan")
    constraints = relationship("SchemaConstraint", back_populates="table", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_schema_table_db_name", "database_id", "table_name", unique=True),
        Index("idx_schema_table_status_entity", "status", "business_entity"),
    )


class SchemaColumn(Base):
    """Metadata for an individual table/view column with HR semantic classifications."""
    __tablename__ = "schema_columns"

    id = Column(Integer, primary_key=True, index=True)
    table_id = Column(Integer, ForeignKey("schema_tables.id", ondelete="CASCADE"), nullable=False, index=True)
    column_name = Column(String(128), nullable=False, index=True)

    # Business naming & definitions
    business_name = Column(String(150), nullable=True)
    description = Column(Text, nullable=True)
    business_definition = Column(Text, nullable=True)
    hr_concept = Column(String(100), nullable=True, index=True)

    # Technical types
    data_type = Column(String(64), nullable=False)  # Raw native SQL dialect type
    normalized_data_type = Column(String(30), default="STRING", nullable=False)
    # STRING, INTEGER, DECIMAL, BOOLEAN, DATE, TIMESTAMP, JSON, OTHER

    is_primary_key = Column(Boolean, default=False, index=True)
    is_foreign_key = Column(Boolean, default=False, index=True)
    is_nullable = Column(Boolean, default=True)
    default_value = Column(String(128), nullable=True)
    ordinal_position = Column(Integer, default=1)

    # Sensitivity & Compliance
    is_sensitive = Column(Boolean, default=False, index=True)
    sensitive_category = Column(String(50), default="NONE", index=True)
    # FINANCIAL, PERSONAL_IDENTIFIER, HEALTH, RESTRICTED, PUBLIC_INTERNAL, NONE

    # Temporal & Date Intelligence
    is_date_field = Column(Boolean, default=False, index=True)
    date_role = Column(String(50), default="NONE", index=True)
    # HIRE_DATE, TERMINATION_DATE, EFFECTIVE_DATE, EXPIRY_DATE, BIRTH_DATE, TRANSACTION_DATE, REVIEW_DATE, PAY_DATE, NONE

    # Metric vs Dimension Classification
    is_metric = Column(Boolean, default=False, index=True)
    default_aggregation = Column(String(20), default="NONE")  # SUM, AVG, COUNT, MIN, MAX, NONE
    is_dimension = Column(Boolean, default=False, index=True)

    # Review & Governance Workflow
    status = Column(String(30), default="AUTO_DISCOVERED", nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationship to table
    table = relationship("SchemaTable", back_populates="columns")

    __table_args__ = (
        Index("idx_schema_col_table_name", "table_id", "column_name", unique=True),
        Index("idx_schema_col_role_metric", "is_metric", "is_dimension"),
    )


class SchemaRelationship(Base):
    """Discovered and inferred relationships between tables."""
    __tablename__ = "schema_relationships"

    id = Column(Integer, primary_key=True, index=True)
    database_id = Column(String(64), nullable=False, index=True)

    source_table_id = Column(Integer, ForeignKey("schema_tables.id", ondelete="CASCADE"), nullable=False, index=True)
    source_table_name = Column(String(128), nullable=False)
    source_column_id = Column(Integer, ForeignKey("schema_columns.id", ondelete="SET NULL"), nullable=True)
    source_column_name = Column(String(128), nullable=False)

    target_table_id = Column(Integer, ForeignKey("schema_tables.id", ondelete="CASCADE"), nullable=False, index=True)
    target_table_name = Column(String(128), nullable=False)
    target_column_id = Column(Integer, ForeignKey("schema_columns.id", ondelete="SET NULL"), nullable=True)
    target_column_name = Column(String(128), nullable=False)

    # Cardinality: ONE_TO_MANY, MANY_TO_ONE, ONE_TO_ONE, MANY_TO_MANY
    relationship_type = Column(String(30), default="MANY_TO_ONE", nullable=False)

    # Source: DATABASE_FOREIGN_KEY, SQL_USAGE, MANUAL
    relationship_source = Column(String(40), default="DATABASE_FOREIGN_KEY", nullable=False, index=True)
    # Confidence: HIGH, MEDIUM, LOW
    confidence = Column(String(20), default="HIGH", nullable=False)
    usage_count = Column(Integer, default=1)
    join_condition_sql = Column(String(256), nullable=True)

    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    __table_args__ = (
        Index("idx_rel_src_tgt", "database_id", "source_table_name", "target_table_name"),
    )


class SchemaIndex(Base):
    """Database indexes on discovered tables."""
    __tablename__ = "schema_indexes"

    id = Column(Integer, primary_key=True, index=True)
    table_id = Column(Integer, ForeignKey("schema_tables.id", ondelete="CASCADE"), nullable=False, index=True)
    index_name = Column(String(128), nullable=False)
    columns_json = Column(JSON, nullable=False)  # list of column names
    is_unique = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    table = relationship("SchemaTable", back_populates="indexes")


class SchemaConstraint(Base):
    """Database constraints (PK, FK, UNIQUE, CHECK)."""
    __tablename__ = "schema_constraints"

    id = Column(Integer, primary_key=True, index=True)
    table_id = Column(Integer, ForeignKey("schema_tables.id", ondelete="CASCADE"), nullable=False, index=True)
    constraint_name = Column(String(128), nullable=False)
    constraint_type = Column(String(30), nullable=False)  # PRIMARY KEY, FOREIGN KEY, UNIQUE, CHECK
    definition = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    table = relationship("SchemaTable", back_populates="constraints")


class SchemaSnapshot(Base):
    """Historical snapshot of a database schema for drift detection and auditing."""
    __tablename__ = "schema_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    database_id = Column(String(64), nullable=False, index=True)
    version_number = Column(Integer, default=1, nullable=False)
    schema_hash = Column(String(64), nullable=False, index=True)  # SHA-256

    table_count = Column(Integer, default=0)
    column_count = Column(Integer, default=0)
    relationship_count = Column(Integer, default=0)

    snapshot_json = Column(JSON, nullable=False)  # Canonical JSON representation of schema structure
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        Index("idx_snapshot_db_ver", "database_id", "version_number", unique=True),
    )


class SchemaChange(Base):
    """Detected schema drift/change between snapshots."""
    __tablename__ = "schema_changes"

    id = Column(Integer, primary_key=True, index=True)
    database_id = Column(String(64), nullable=False, index=True)
    snapshot_id = Column(Integer, ForeignKey("schema_snapshots.id", ondelete="CASCADE"), nullable=False, index=True)

    # Change types:
    # TABLE_ADDED, TABLE_REMOVED, TABLE_MODIFIED,
    # COLUMN_ADDED, COLUMN_REMOVED, COLUMN_TYPE_CHANGED, COLUMN_NULLABILITY_CHANGED,
    # RELATIONSHIP_ADDED, RELATIONSHIP_REMOVED
    change_type = Column(String(40), nullable=False, index=True)
    target_name = Column(String(128), nullable=False)  # table or table.column
    details_json = Column(JSON, nullable=True)  # old vs new metadata
    detected_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class SchemaUsageMetric(Base):
    """Usage frequency intelligence mined from historical and generated SQL queries."""
    __tablename__ = "schema_usage_metrics"

    id = Column(Integer, primary_key=True, index=True)
    database_id = Column(String(64), nullable=False, index=True)

    # Entity Type: TABLE, COLUMN, JOIN
    entity_type = Column(String(20), nullable=False, index=True)
    entity_name = Column(String(150), nullable=False, index=True)  # table_name, table.column, or tblA->tblB
    query_count = Column(Integer, default=1)
    last_queried_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    __table_args__ = (
        Index("idx_usage_db_type_name", "database_id", "entity_type", "entity_name", unique=True),
    )
