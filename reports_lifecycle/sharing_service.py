"""Sharing and Granular Access Control (ACL) Service for Module 12 Reports."""


from sqlalchemy.orm import Session

from backend.auth.authorization import AuthorizationService
from backend.database.models import User
from backend.database.models_reports import ReportAccess, SavedReport

from .schemas import ReportAccessCreateRequest

LEVEL_WEIGHTS = {
    "NONE": 0,
    "VIEW": 1,
    "EXPORT": 2,
    "EDIT": 3,
    "ADMIN": 4
}


class ReportSharingService:
    """Evaluates and manages report access control lists (ACLs)."""

    @classmethod
    def get_user_access_level(cls, db: Session, report: SavedReport, user: User | None) -> str:
        """Determines effective access level for a user on a given report."""
        if user is None:
            return "NONE"

        # Superadmin override
        if getattr(user, "role", "") == "admin" or getattr(user, "is_admin", False):
            return "ADMIN"

        # Check system admin permission
        if AuthorizationService.has_permission(db, user, "admin:all"):
            return "ADMIN"

        # Report author/owner has ADMIN
        if report.created_by is not None and report.created_by == user.id:
            return "ADMIN"
        if report.author_username and report.author_username == user.username:
            return "ADMIN"

        # Query explicit ACL rules
        rules = db.query(ReportAccess).filter(
            ReportAccess.saved_report_id == report.id
        ).all()

        max_weight = 0
        best_level = "NONE"

        for rule in rules:
            matched = False
            if rule.user_id is not None and rule.user_id == user.id or rule.role_name and (rule.role_name == getattr(user, "role", "") or rule.role_name == "*"):
                matched = True

            if matched:
                weight = LEVEL_WEIGHTS.get(rule.access_level.upper(), 0)
                if weight > max_weight:
                    max_weight = weight
                    best_level = rule.access_level.upper()

        return best_level

    @classmethod
    def can_view(cls, access_level: str) -> bool:
        return LEVEL_WEIGHTS.get(access_level.upper(), 0) >= 1

    @classmethod
    def can_export(cls, access_level: str) -> bool:
        return LEVEL_WEIGHTS.get(access_level.upper(), 0) >= 2

    @classmethod
    def can_edit(cls, access_level: str) -> bool:
        return LEVEL_WEIGHTS.get(access_level.upper(), 0) >= 3

    @classmethod
    def can_admin(cls, access_level: str) -> bool:
        return LEVEL_WEIGHTS.get(access_level.upper(), 0) >= 4

    @classmethod
    def grant_access(
        cls,
        db: Session,
        report: SavedReport,
        req: ReportAccessCreateRequest,
        granter: User
    ) -> ReportAccess:
        """Grants or updates sharing ACL for user or role."""
        if not req.user_id and not req.role_name:
            raise ValueError("Either user_id or role_name must be specified for report sharing.")

        # Check if an existing rule matches
        query = db.query(ReportAccess).filter(
            ReportAccess.saved_report_id == report.id
        )
        if req.user_id:
            query = query.filter(ReportAccess.user_id == req.user_id)
        else:
            query = query.filter(ReportAccess.role_name == req.role_name)

        existing = query.first()
        if existing:
            existing.access_level = req.access_level.upper()
            existing.granted_by = granter.username
            db.commit()
            db.refresh(existing)
            return existing

        new_rule = ReportAccess(
            saved_report_id=report.id,
            user_id=req.user_id,
            role_name=req.role_name,
            access_level=req.access_level.upper(),
            granted_by=granter.username
        )
        db.add(new_rule)
        db.commit()
        db.refresh(new_rule)
        return new_rule

    @classmethod
    def revoke_access(
        cls,
        db: Session,
        report: SavedReport,
        access_id: int
    ) -> bool:
        """Revokes a sharing ACL rule."""
        rule = db.query(ReportAccess).filter(
            ReportAccess.id == access_id,
            ReportAccess.saved_report_id == report.id
        ).first()
        if not rule:
            return False

        db.delete(rule)
        db.commit()
        return True

    @classmethod
    def list_access_rules(cls, db: Session, report: SavedReport) -> list[ReportAccess]:
        return db.query(ReportAccess).filter(
            ReportAccess.saved_report_id == report.id
        ).all()
