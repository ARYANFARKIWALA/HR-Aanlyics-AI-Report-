"""Server-side session management, idle timeout, and brute-force lockout."""

import secrets
import datetime
from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from ..database.models import User
from ..database.models_auth import UserSession
from .security_audit import SecurityAuditService

DEFAULT_SESSION_IDLE_MINUTES = 30
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


class SessionManager:
    """Handles session creation, validation, idle timeouts, and account lockouts."""

    @staticmethod
    def is_account_locked(user: User) -> Tuple[bool, int]:
        """Checks if a user's account is currently locked out."""
        if not user.locked_until:
            return False, 0

        now = datetime.datetime.now(datetime.UTC)
        locked_until = user.locked_until
        # Handle naive datetime from SQLite
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=datetime.UTC)

        if now < locked_until:
            remaining = int((locked_until - now).total_seconds())
            return True, remaining
        return False, 0

    @staticmethod
    def record_login_failure(
        db: Session,
        user: User,
        ip_address: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Increments failed login counter and triggers lockout if threshold reached."""
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        now = datetime.datetime.now(datetime.UTC)

        if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = now + datetime.timedelta(minutes=LOCKOUT_MINUTES)
            db.commit()
            SecurityAuditService.log_event(
                db=db,
                event_type="ACCOUNT_LOCKED",
                status="BLOCKED",
                user_id=user.id,
                username=user.username,
                ip_address=ip_address,
                details={
                    "attempts": user.failed_login_attempts,
                    "locked_until": user.locked_until.isoformat(),
                    "lockout_minutes": LOCKOUT_MINUTES
                }
            )
            return True, f"Account locked due to {MAX_FAILED_ATTEMPTS} failed attempts. Try again in {LOCKOUT_MINUTES} minutes."

        db.commit()
        SecurityAuditService.log_event(
            db=db,
            event_type="LOGIN_FAILURE",
            status="FAILURE",
            user_id=user.id,
            username=user.username,
            ip_address=ip_address,
            details={"attempts": user.failed_login_attempts, "remaining": MAX_FAILED_ATTEMPTS - user.failed_login_attempts}
        )
        return False, f"Invalid password. {MAX_FAILED_ATTEMPTS - user.failed_login_attempts} attempts remaining."

    @staticmethod
    def record_login_success(
        db: Session,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        idle_minutes: int = DEFAULT_SESSION_IDLE_MINUTES
    ) -> UserSession:
        """Resets failed login counters and generates a new session token."""
        user.failed_login_attempts = 0
        user.locked_until = None

        now = datetime.datetime.now(datetime.UTC)
        session_token = secrets.token_urlsafe(48)
        session = UserSession(
            session_token=session_token,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=now,
            expires_at=now + datetime.timedelta(minutes=idle_minutes),
            last_active=now,
            is_revoked=False
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        SecurityAuditService.log_event(
            db=db,
            event_type="LOGIN_SUCCESS",
            status="SUCCESS",
            user_id=user.id,
            username=user.username,
            ip_address=ip_address,
            details={"session_token_prefix": session_token[:8] + "..."}
        )
        return session

    @staticmethod
    def validate_session(
        db: Session,
        session_token: str,
        idle_minutes: int = DEFAULT_SESSION_IDLE_MINUTES
    ) -> Optional[UserSession]:
        """Validates session token and refreshes idle expiration window."""
        session = db.query(UserSession).filter(
            UserSession.session_token == session_token
        ).first()

        if not session or session.is_revoked:
            return None

        now = datetime.datetime.now(datetime.UTC)
        expires_at = session.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=datetime.UTC)

        if now > expires_at:
            session.is_revoked = True
            db.commit()
            SecurityAuditService.log_event(
                db=db,
                event_type="SESSION_EXPIRED",
                status="EXPIRED",
                user_id=session.user_id,
                details={"session_id": session.id}
            )
            return None

        # Sliding session expiration
        session.last_active = now
        session.expires_at = now + datetime.timedelta(minutes=idle_minutes)
        db.commit()
        return session

    @staticmethod
    def revoke_session(db: Session, session_token: str) -> bool:
        """Revokes a single session."""
        session = db.query(UserSession).filter(
            UserSession.session_token == session_token
        ).first()
        if session and not session.is_revoked:
            session.is_revoked = True
            db.commit()
            SecurityAuditService.log_event(
                db=db,
                event_type="SESSION_REVOKED",
                status="SUCCESS",
                user_id=session.user_id,
                details={"session_id": session.id}
            )
            return True
        return False

    @staticmethod
    def revoke_all_user_sessions(db: Session, user_id: int) -> int:
        """Revokes all active sessions for a user (e.g. on password reset or account disable)."""
        sessions = db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_revoked == False
        ).all()
        count = len(sessions)
        for s in sessions:
            s.is_revoked = True
        db.commit()
        return count
