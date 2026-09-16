"""High-level Report Lifecycle CRUD Service for Module 12."""

import datetime
import json
import uuid

from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.database.models import User
from backend.database.models_reports import ReportAccess, SavedReport

from .schemas import ReportCreateRequest, ReportUpdateRequest
from .sharing_service import ReportSharingService
from .version_service import ReportVersionService


class ReportLifecycleService:
    """Manages report lifecycle operations: creation, updates, duplication, archiving, and deletion."""

    @classmethod
    def create_report(
        cls,
        db: Session,
        req: ReportCreateRequest,
        user: User | None = None
    ) -> SavedReport:
        """Creates a new enterprise saved report with initial version snapshot and owner ACL."""
        report_id = f"rep_{uuid.uuid4().hex[:12]}"
        
        layout_str = None
        if req.layout_config is not None:
            if isinstance(req.layout_config, dict):
                layout_str = json.dumps(req.layout_config)
            else:
                layout_str = str(req.layout_config)

        report = SavedReport(
            report_id=report_id,
            title=req.title,
            description=req.description,
            category=req.category,
            database_id=req.database_id,
            sql_query=req.sql_query,
            layout_config=layout_str,
            created_by=user.id if user else None,
            author_username=user.username if user else "system",
            current_version=1,
            is_archived=False,
            is_deleted=False,
            created_at=datetime.datetime.now(datetime.UTC),
            updated_at=datetime.datetime.now(datetime.UTC)
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        # Create initial Version 1 snapshot
        ReportVersionService.create_snapshot(
            db=db,
            report=report,
            modifier=user,
            change_summary="Initial creation"
        )

        # Create Owner Access Rule
        if user:
            owner_rule = ReportAccess(
                saved_report_id=report.id,
                user_id=user.id,
                access_level="ADMIN",
                granted_by="system"
            )
            db.add(owner_rule)
            db.commit()

        report.user_access_level = "ADMIN"
        return report

    @classmethod
    def get_report(
        cls,
        db: Session,
        report_id: str,
        user: User | None = None
    ) -> SavedReport:
        """Retrieves a saved report by report_id checking view clearance."""
        report = db.query(SavedReport).filter(
            SavedReport.report_id == report_id,
            SavedReport.is_deleted == False
        ).first()
        if not report:
            raise KeyError(f"Report '{report_id}' not found.")

        level = ReportSharingService.get_user_access_level(db, report, user)
        if not ReportSharingService.can_view(level):
            raise PermissionError(f"User lacks VIEW permission for report '{report_id}'.")

        report.user_access_level = level
        return report

    @classmethod
    def list_reports(
        cls,
        db: Session,
        user: User | None = None,
        category: str | None = None,
        search: str | None = None,
        include_archived: bool = False
    ) -> list[SavedReport]:
        """Lists all reports accessible to the user, applying category/search/archive filters."""
        query = db.query(SavedReport).filter(SavedReport.is_deleted == False)

        if not include_archived:
            query = query.filter(SavedReport.is_archived == False)

        if category and category != "All":
            query = query.filter(SavedReport.category == category)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    SavedReport.title.ilike(search_pattern),
                    SavedReport.description.ilike(search_pattern),
                    SavedReport.category.ilike(search_pattern)
                )
            )

        all_reports = query.order_by(SavedReport.updated_at.desc()).all()
        accessible_reports = []

        for rep in all_reports:
            level = ReportSharingService.get_user_access_level(db, rep, user)
            if ReportSharingService.can_view(level):
                rep.user_access_level = level
                accessible_reports.append(rep)

        return accessible_reports

    @classmethod
    def update_report(
        cls,
        db: Session,
        report_id: str,
        req: ReportUpdateRequest,
        user: User | None = None
    ) -> SavedReport:
        """Updates a report, incrementing version and creating an immutable version snapshot."""
        report = cls.get_report(db, report_id, user)
        level = getattr(report, "user_access_level", ReportSharingService.get_user_access_level(db, report, user))
        if not ReportSharingService.can_edit(level):
            raise PermissionError(f"User lacks EDIT permission for report '{report_id}'.")

        if req.title is not None:
            report.title = req.title
        if req.description is not None:
            report.description = req.description
        if req.category is not None:
            report.category = req.category
        if req.database_id is not None:
            report.database_id = req.database_id
        if req.sql_query is not None:
            report.sql_query = req.sql_query
        if req.layout_config is not None:
            if isinstance(req.layout_config, dict):
                report.layout_config = json.dumps(req.layout_config)
            else:
                report.layout_config = str(req.layout_config)

        report.current_version += 1
        report.updated_at = datetime.datetime.now(datetime.UTC)
        db.commit()
        db.refresh(report)

        # Snapshot new version
        ReportVersionService.create_snapshot(
            db=db,
            report=report,
            modifier=user,
            change_summary=req.change_summary or f"Updated to version {report.current_version}"
        )

        report.user_access_level = level
        return report

    @classmethod
    def duplicate_report(
        cls,
        db: Session,
        report_id: str,
        user: User,
        new_title: str | None = None
    ) -> SavedReport:
        """Duplicates a report, resetting version to 1 and setting requester as owner."""
        source = cls.get_report(db, report_id, user)
        # Check that user can view source
        level = getattr(source, "user_access_level", ReportSharingService.get_user_access_level(db, source, user))
        if not ReportSharingService.can_view(level):
            raise PermissionError("User lacks access to duplicate this report.")

        dup_title = new_title or f"Copy of {source.title}"
        create_req = ReportCreateRequest(
            title=dup_title,
            description=f"Duplicated from {source.title} (v{source.current_version})",
            category=source.category,
            database_id=source.database_id,
            sql_query=source.sql_query,
            layout_config=source.layout_config
        )
        return cls.create_report(db, create_req, user=user)

    @classmethod
    def archive_report(
        cls,
        db: Session,
        report_id: str,
        user: User,
        archive: bool = True
    ) -> SavedReport:
        """Archives or unarchives a report (requires ADMIN clearance)."""
        report = cls.get_report(db, report_id, user)
        level = getattr(report, "user_access_level", ReportSharingService.get_user_access_level(db, report, user))
        if not ReportSharingService.can_admin(level):
            raise PermissionError("ADMIN clearance required to archive/unarchive reports.")

        report.is_archived = archive
        report.updated_at = datetime.datetime.now(datetime.UTC)
        db.commit()
        db.refresh(report)
        report.user_access_level = level
        return report

    @classmethod
    def delete_report(
        cls,
        db: Session,
        report_id: str,
        user: User
    ) -> bool:
        """Soft-deletes a report (requires ADMIN clearance)."""
        report = cls.get_report(db, report_id, user)
        level = getattr(report, "user_access_level", ReportSharingService.get_user_access_level(db, report, user))
        if not ReportSharingService.can_admin(level):
            raise PermissionError("ADMIN clearance required to delete reports.")

        report.is_deleted = True
        report.updated_at = datetime.datetime.now(datetime.UTC)
        db.commit()
        return True
