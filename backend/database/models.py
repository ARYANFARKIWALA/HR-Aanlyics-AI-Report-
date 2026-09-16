"""SQLAlchemy ORM Data Models for HR Analytics and Enterprise SQL Catalog."""

import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Date, DateTime,
    ForeignKey, Text, Index
)
from sqlalchemy.orm import relationship
from .connection import Base


class User(Base):
    """Application users with role-based access control."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(128), unique=True, nullable=False)
    hashed_password = Column(String(256), nullable=False)
    full_name = Column(String(128), nullable=False)
    role = Column(String(32), default="hr_analyst", nullable=False)  # admin, hr_manager, hr_analyst, executive
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    department = relationship("Department", back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="user")


class Department(Base):
    """Organizational departments and cost centers."""
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    cost_center = Column(String(50), nullable=False)
    budget = Column(Float, default=0.0)
    manager_name = Column(String(100), nullable=True)
    location = Column(String(100), default="Headquarters")

    employees = relationship("Employee", back_populates="department")
    users = relationship("User", back_populates="department")


class JobProfile(Base):
    """Job role architecture and salary bands."""
    __tablename__ = "job_profiles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), unique=True, nullable=False)
    job_family = Column(String(50), nullable=False)  # Engineering, Sales, HR, Finance, etc.
    salary_grade = Column(String(10), nullable=False)  # L1 to L7
    min_salary = Column(Float, nullable=False)
    mid_salary = Column(Float, nullable=False)
    max_salary = Column(Float, nullable=False)

    employees = relationship("Employee", back_populates="job_profile")


class Employee(Base):
    """Core Employee record with effective-dating history."""
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    employee_number = Column(String(20), nullable=False, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100), nullable=False)
    gender = Column(String(20), nullable=False)  # Male, Female, Non-Binary
    ethnicity = Column(String(50), default="Undisclosed")
    hire_date = Column(Date, nullable=False)
    termination_date = Column(Date, nullable=True)
    status = Column(String(20), default="Active", nullable=False)  # Active, Terminated, On Leave
    attrition_type = Column(String(20), default="None")  # Voluntary, Involuntary, None
    attrition_reason = Column(String(100), default="N/A")
    employment_type = Column(String(30), default="Full-Time")  # Full-Time, Part-Time, Contractor
    work_location = Column(String(30), default="Hybrid")  # Remote, Hybrid, On-Site

    # Effective Dating Attributes
    effective_start_date = Column(Date, nullable=False)
    effective_end_date = Column(Date, nullable=False)
    is_current = Column(Boolean, default=True, index=True)

    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    job_profile_id = Column(Integer, ForeignKey("job_profiles.id"), nullable=False)
    manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)

    department = relationship("Department", back_populates="employees")
    job_profile = relationship("JobProfile", back_populates="employees")
    compensation_history = relationship("CompensationHistory", back_populates="employee", cascade="all, delete-orphan")
    performance_reviews = relationship("PerformanceReview", back_populates="employee", cascade="all, delete-orphan")
    leave_records = relationship("LeaveRecord", back_populates="employee", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_emp_eff_dating", "employee_number", "effective_start_date", "effective_end_date"),
    )


class CompensationHistory(Base):
    """Salary revision track with effective dates."""
    __tablename__ = "compensation_history"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    base_salary = Column(Float, nullable=False)
    bonus = Column(Float, default=0.0)
    currency = Column(String(10), default="USD")
    compa_ratio = Column(Float, default=1.0)
    change_reason = Column(String(50), default="Annual Merit")  # Promotion, Merit, Market Adjustment, Hire
    effective_date = Column(Date, nullable=False)

    employee = relationship("Employee", back_populates="compensation_history")


class PerformanceReview(Base):
    """Employee review scores and goal achievement."""
    __tablename__ = "performance_reviews"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    review_cycle = Column(String(20), nullable=False)  # 2023-Annual, 2024-MidYear, etc.
    review_date = Column(Date, nullable=False)
    rating = Column(Integer, nullable=False)  # 1 to 5
    potential_score = Column(Integer, default=2)  # 1 to 3
    goals_achieved_pct = Column(Float, default=100.0)
    feedback_summary = Column(Text, default="Solid performance throughout the cycle.")

    employee = relationship("Employee", back_populates="performance_reviews")


class LeaveRecord(Base):
    """Time-off tracking."""
    __tablename__ = "leave_records"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    leave_type = Column(String(30), nullable=False)  # Annual, Sick, Parental, Unpaid
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days_taken = Column(Float, nullable=False)
    status = Column(String(20), default="Approved")

    employee = relationship("Employee", back_populates="leave_records")


class SQLRepository(Base):
    """Catalog of organization's verified historical HR SQL reports."""
    __tablename__ = "sql_repository"

    id = Column(Integer, primary_key=True, index=True)
    report_title = Column(String(150), unique=True, nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)  # Headcount, Attrition, Compensation, Performance, Diversity
    business_description = Column(Text, nullable=False)
    raw_sql = Column(Text, nullable=False)
    business_rules_explained = Column(Text, nullable=False)
    joins_explained = Column(Text, nullable=False)
    effective_dating_explained = Column(Text, nullable=False)
    tags = Column(String(256), default="")  # comma separated
    author = Column(String(100), default="Enterprise BI Team")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class AuditLog(Base):
    """Compliance audit trail for natural language queries and executed SQL."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    username = Column(String(64), nullable=False)
    user_role = Column(String(32), nullable=False)
    natural_query = Column(Text, nullable=False)
    generated_sql = Column(Text, nullable=True)
    execution_time_ms = Column(Float, default=0.0)
    row_count = Column(Integer, default=0)
    status = Column(String(30), default="SUCCESS")  # SUCCESS, REJECTED, FAILED
    error_details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    user = relationship("User", back_populates="audit_logs")
