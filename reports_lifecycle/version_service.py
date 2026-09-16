"""Version management and non-destructive restore service for Module 12."""

import datetime

from sqlalchemy.orm import Session

from backend.database.models import User
from backend.database.models_reports import SavedReport, SavedReportVersion


class ReportVersionService:
    """Manages immutable snapshots and non-destructive rollbacks."""

    @classmethod
    def create_snapshot(
        cls,
        db: Session,
        report: SavedReport,
        modifier: User | None = None,
        change_summary: str = "Update"
    ) -> SavedReportVersion:
        """Takes an immutable snapshot of the report's current state."""
        version = SavedReportVersion(
            saved_report_id=report.id,
            version_number=report.current_version,
            title=report.title,
            sql_query=report.sql_query,
            layout_config=report.layout_config,
            modified_by=modifier.id if modifier else None,
            modified_by_username=modifier.username if modifier else "system",
            change_summary=change_summary,
            created_at=datetime.datetime.now(datetime.UTC)
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        return version

    @classmethod
    def list_versions(cls, db: Session, report: SavedReport) -> list[SavedReportVersion]:
        """Lists all recorded versions of a report, latest first."""
        return db.query(SavedReportVersion).filter(
            SavedReportVersion.saved_report_id == report.id
        ).order_by(SavedReportVersion.version_number.desc()).all()

    @classmethod
    def get_version(cls, db: Session, report: SavedReport, version_number: int) -> SavedReportVersion | None:
        return db.query(SavedReportVersion).filter(
            SavedReportVersion.saved_report_id == report.id,
            SavedReportVersion.version_number == version_number
        ).first()

    @classmethod
    def restore_version(
        cls,
        db: Session,
        report: SavedReport,
        version_number: int,
        modifier: User
    ) -> SavedReport:
        """Non-destructive restore: creates a NEW version with target version's contents."""
        target_version = cls.get_version(db, report, version_number)
        if not target_version:
            raise ValueError(f"Version {version_number} does not exist for report {report.report_id}")

        # Increment version number
        report.current_version += 1
        report.title = target_version.title
        report.sql_query = target_version.sql_query
        report.layout_config = target_version.layout_config
        report.updated_at = datetime.datetime.now(datetime.UTC)

        # Create new version entry reflecting restore
        new_version = SavedReportVersion(
            saved_report_id=report.id,
            version_number=report.current_version,
            title=report.title,
            sql_query=report.sql_query,
            layout_config=report.layout_config,
            modified_by=modifier.id,
            modified_by_username=modifier.username,
            change_summary=f"Restored from version {version_number}",
            created_at=datetime.datetime.now(datetime.UTC)
        )
        db.add(new_version)
        db.commit()
        db.refresh(report)
        return report
