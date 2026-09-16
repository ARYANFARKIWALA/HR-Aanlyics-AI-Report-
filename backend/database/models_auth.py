"""SQLAlchemy models for Module 11 - Authentication, Authorization, RBAC, ABAC, and Security Audit."""

import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    ForeignKey, Text, Index
)
from sqlalchemy.orm import relationship
from .connection import Base


class Organization(Base):
    """Multi-tenant organization entity."""
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), unique=True, nullable=False)
    code = Column(String(64), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Role(Base):
    """System and custom roles."""
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")


class Permission(Base):
    """Granular system permissions."""
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    category = Column(String(64), nullable=False, index=True)  # SQL, Report, Admin, Rule, Schema, Analytics
    description = Column(String(255), nullable=True)

    roles = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")


class RolePermission(Base):
    """Mapping between roles and permissions."""
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False)

    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="roles")

    __table_args__ = (
        Index("idx_role_permission", "role_id", "permission_id", unique=True),
    )


class UserDatabaseAccess(Base):
    """Explicit per-user database access permissions (ABAC/Data isolation)."""
    __tablename__ = "user_database_access"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    database_id = Column(String(64), nullable=False, index=True)
    can_read = Column(Boolean, default=True)
    can_write = Column(Boolean, default=False)
    can_execute = Column(Boolean, default=True)
    granted_by = Column(String(64), nullable=True)
    granted_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        Index("idx_user_db_access", "user_id", "database_id", unique=True),
    )


class ColumnPermission(Base):
    """Column-level security (CLS) rules: column allowlist and data masking."""
    __tablename__ = "column_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    database_id = Column(String(64), nullable=False, index=True)
    table_name = Column(String(128), nullable=False, index=True)
    column_name = Column(String(128), nullable=False, index=True)
    is_allowed = Column(Boolean, default=True)  # True = selectable, False = rejected
    is_masked = Column(Boolean, default=False)  # True = apply masking function
    mask_type = Column(String(32), default="partial")  # "full", "partial", "hash", "null"


class RowAccessRule(Base):
    """Row-level security (RLS) predicates appended to queries."""
    __tablename__ = "row_access_rules"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    database_id = Column(String(64), nullable=False, index=True)
    table_name = Column(String(128), nullable=False, index=True)
    filter_expression = Column(Text, nullable=False)  # e.g. "department_id = {user.department_id}"
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)


class UserSession(Base):
    """Server-side active user sessions with idle timeout and revocation."""
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_token = Column(String(128), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_active = Column(DateTime, default=datetime.datetime.utcnow)
    is_revoked = Column(Boolean, default=False)


class SecurityAuditLog(Base):
    """Security and compliance audit trail."""
    __tablename__ = "security_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    username = Column(String(64), nullable=True, index=True)
    ip_address = Column(String(64), nullable=True)
    status = Column(String(32), nullable=False)  # SUCCESS, FAILURE, BLOCKED
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
