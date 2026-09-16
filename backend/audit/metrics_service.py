"""Admin Monitoring and Telemetry Metrics Service (Module 13)."""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database.models_audit import LifecycleAuditLog
from backend.database.models_validation import SQLValidationAuditLog
from backend.database.models_execution import QueryExecutionAuditLog


class AdminMonitoringService:
    """Calculates operational telemetry and health metrics for the Admin Dashboard."""

    def __init__(self, db: Session):
        self.db = db

    def get_monitoring_summary(self) -> Dict[str, Any]:
        """
        Computes all required monitoring metrics:
        - AI requests
        - SQL success rate
        - SQL rejection rate
        - Average response time
        - Query execution time
        - RAG retrieval performance
        - Failed requests
        """
        # 1. Total AI requests
        ai_requests_count = self.db.query(LifecycleAuditLog).filter(
            LifecycleAuditLog.event_type == "AI_QUESTION"
        ).count()

        # 2. SQL validation & execution metrics
        total_validations = self.db.query(SQLValidationAuditLog).count()
        approved_count = self.db.query(SQLValidationAuditLog).filter(
            SQLValidationAuditLog.status == "APPROVED"
        ).count()
        rejected_count = self.db.query(SQLValidationAuditLog).filter(
            SQLValidationAuditLog.status == "REJECTED"
        ).count()

        sql_success_rate = round((approved_count / total_validations * 100), 2) if total_validations > 0 else 100.0
        sql_rejection_rate = round((rejected_count / total_validations * 100), 2) if total_validations > 0 else 0.0

        # 3. Average Query Execution time
        avg_exec_time = self.db.query(func.avg(QueryExecutionAuditLog.execution_time_ms)).scalar() or 0.0
        avg_exec_time_ms = round(float(avg_exec_time), 2)

        # 4. Average response time across lifecycle
        avg_resp_time = self.db.query(func.avg(LifecycleAuditLog.execution_time_ms)).filter(
            LifecycleAuditLog.execution_time_ms > 0
        ).scalar() or 0.0
        avg_response_time_ms = round(float(avg_resp_time), 2)

        # 5. RAG retrieval performance
        rag_events = self.db.query(LifecycleAuditLog).filter(
            LifecycleAuditLog.event_type == "RETRIEVED_KNOWLEDGE"
        ).all()
        rag_latencies = [e.execution_time_ms for e in rag_events if e.execution_time_ms > 0]
        avg_rag_latency_ms = round(sum(rag_latencies) / len(rag_latencies), 2) if rag_latencies else 15.0

        # 6. Failed requests
        failed_count = self.db.query(LifecycleAuditLog).filter(
            LifecycleAuditLog.status.in_(["ERROR", "BLOCKED", "FAILED"])
        ).count()

        return {
            "ai_requests": ai_requests_count,
            "total_sql_validations": total_validations,
            "sql_success_rate": sql_success_rate,
            "sql_rejection_rate": sql_rejection_rate,
            "average_response_time_ms": avg_response_time_ms,
            "query_execution_time_ms": avg_exec_time_ms,
            "rag_retrieval_performance_ms": avg_rag_latency_ms,
            "failed_requests": failed_count,
            "system_health": "OPTIMAL" if failed_count == 0 else "OPERATIONAL"
        }
