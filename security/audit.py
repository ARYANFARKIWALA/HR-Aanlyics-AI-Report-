"""Enterprise Audit Logger for Compliance and Observability."""

from typing import Optional, List, Dict, Any
import datetime
from sqlalchemy.orm import Session
from backend.database.models import AuditLog


class AuditLogger:
    """Logs all user interactions, AI prompts, SQL queries, and execution latencies."""

    @classmethod
    def log_query(
        cls,
        session: Session,
        username: str,
        user_role: str,
        natural_query: str,
        generated_sql: Optional[str],
        execution_time_ms: float,
        row_count: int,
        status: str = "SUCCESS",
        error_details: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> AuditLog:
        """Persists audit record to the database."""
        try:
            log_entry = AuditLog(
                user_id=user_id,
                username=username,
                user_role=user_role,
                natural_query=natural_query,
                generated_sql=generated_sql,
                execution_time_ms=round(execution_time_ms, 2),
                row_count=row_count,
                status=status,
                error_details=error_details,
                timestamp=datetime.datetime.utcnow()
            )
            session.add(log_entry)
            session.commit()
            session.refresh(log_entry)
            return log_entry
        except Exception as exc:
            session.rollback()
            print(f"[AuditLogger] Failed to write audit log: {exc}")
            return None

    @classmethod
    def get_recent_logs(cls, session: Session, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves recent audit logs for security review."""
        logs = session.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
        return [
            {
                "id": l.id,
                "username": l.username,
                "user_role": l.user_role,
                "natural_query": l.natural_query,
                "generated_sql": l.generated_sql,
                "execution_time_ms": l.execution_time_ms,
                "row_count": l.row_count,
                "status": l.status,
                "error_details": l.error_details,
                "timestamp": l.timestamp.strftime("%Y-%m-%d %H:%M:%S") if l.timestamp else ""
            }
            for l in logs
        ]
