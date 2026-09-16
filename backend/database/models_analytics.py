"""SQLAlchemy ORM model for Module 9 - HR Analytics Engine Audit."""

import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text

from .connection import Base


class AnalyticsAuditLog(Base):
    """Audit log of all analytical and insight generation runs."""
    __tablename__ = "analytics_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(64), unique=True, nullable=False, index=True)
    execution_id = Column(String(64), ForeignKey("query_execution_audit_logs.execution_id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    username = Column(String(64), nullable=True)

    dataset_shape = Column(String(64), nullable=True)  # e.g. "120 rows x 8 cols"
    kpis_computed = Column(Text, nullable=True)  # JSON summary of top computed KPIs
    insights_generated_count = Column(Integer, default=0)
    data_quality_score = Column(Float, default=100.0)

    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_analytics_lookup", "analysis_id", "execution_id"),
    )
