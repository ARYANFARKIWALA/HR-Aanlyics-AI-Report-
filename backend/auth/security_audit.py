"""Security audit trail logging service."""

import datetime
import json
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from ..database.models_auth import SecurityAuditLog


class SecurityAuditService:
    """Records security-critical events for compliance and anomaly detection."""

    @staticmethod
    def log_event(
        db: Session,
        event_type: str,
        status: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any] | str] = None,
    ) -> SecurityAuditLog:
        """Appends a new security audit record to the database."""
        details_str = (
            json.dumps(details, default=str)
            if isinstance(details, dict)
            else (str(details) if details else None)
        )

        entry = SecurityAuditLog(
            event_type=event_type,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            status=status,
            details=details_str,
            created_at=datetime.datetime.now(datetime.UTC),
        )
        try:
            db.add(entry)
            db.commit()
            db.refresh(entry)
        except Exception:
            db.rollback()
        return entry
