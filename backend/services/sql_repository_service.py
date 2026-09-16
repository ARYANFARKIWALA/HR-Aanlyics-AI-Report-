"""Module 2: SQL Repository & Knowledge Management Service.

Orchestrates:
- Manual, file, and bulk SQL report imports
- SQLGlot parsing, AST metadata extraction & complexity scoring
- Duplicate and near-duplicate detection via normalized SQL hashing
- Version control with historical diff comparison
- Role-based approval and rejection workflows
- Preparation of RAG-ready knowledge documents
- Audit logging for all administrative repository events
"""

import datetime
import difflib
import json
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from ..database.models import User, AuditLog
from ..database.models_repo import (
    SQLReport, SQLReportMetadata, SQLReportParameter,
    SQLReportVersion, SQLApproval, SQLCategory, Tag, SQLReportTag
)
from ..database.connection_manager import connection_manager
from sql.parser import SQLParser, ExtractedSQLMetadata
from sql.normalizer import SQLNormalizer
from sql.file_parser import SQLFileParser, ParsedSQLFileEntry
from rag.sql_knowledge_builder import SQLKnowledgeBuilder, SQLKnowledgeDocument


class SQLRepositoryService:
    """Enterprise service managing the existing SQL knowledge repository."""

    # -------------------------------------------------------------
    # 1. Report ID Generation
    # -------------------------------------------------------------
    @classmethod
    def generate_report_code(cls, session: Session) -> str:
        """Generates sequential, database-safe ID: SQLRPT-000001."""
        max_id = session.query(func.max(SQLReport.id)).scalar() or 0
        return f"SQLRPT-{(max_id + 1):06d}"

    # -------------------------------------------------------------
    # 2. Add / Import Single SQL Report
    # -------------------------------------------------------------
    @classmethod
    def create_report(
        cls,
        session: Session,
        report_name: str,
        sql_query: str,
        database_id: str,
        user: User,
        description: str = "",
        business_purpose: str = "",
        category: str = "Other",
        tags: Optional[List[str]] = None,
        organization_id: str = "org_default"
    ) -> Tuple[SQLReport, Dict[str, Any]]:
        """Imports and catalogs an existing SQL report without executing it."""
        # Get target database dialect from Module 1
        dialect_rules = connection_manager.get_dialect_rules(database_id)
        dialect_name = dialect_rules.dialect_name if dialect_rules else "sqlite"

        # 1. Normalize SQL and generate hash for duplicate detection
        normalized_sql, sql_hash = SQLNormalizer.normalize(sql_query, dialect=dialect_name)

        # 2. Duplicate Detection Check
        existing_dup = session.query(SQLReport).filter(
            SQLReport.database_id == database_id,
            SQLReport.sql_hash == sql_hash
        ).first()

        dup_info = {
            "is_duplicate": existing_dup is not None,
            "duplicate_report_code": existing_dup.report_code if existing_dup else None,
            "duplicate_report_name": existing_dup.report_name if existing_dup else None,
        }

        # 3. SQLGlot Parsing and Metadata Extraction (Non-executing)
        parsed_meta: ExtractedSQLMetadata = SQLParser.parse_query(sql_query, read_dialect=dialect_name)

        initial_status = "PENDING_REVIEW" if parsed_meta.is_valid else "INVALID"

        report_code = cls.generate_report_code(session)
        report = SQLReport(
            report_code=report_code,
            organization_id=organization_id,
            database_id=database_id,
            report_name=report_name.strip() or f"Report {report_code}",
            description=description.strip() or "Existing organization SQL report.",
            business_purpose=business_purpose.strip() or description.strip(),
            category=category or "Other",
            sql_query=sql_query.strip(),
            normalized_sql=normalized_sql,
            sql_hash=sql_hash,
            status=initial_status,
            version=1,
            is_valid=parsed_meta.is_valid,
            validation_error=parsed_meta.validation_error,
            validated_at=datetime.datetime.utcnow(),
            owner_id=user.id if user else None
        )
        session.add(report)
        session.flush()

        # 4. Save Extracted Metadata
        metadata_record = SQLReportMetadata(
            report_id=report.id,
            table_count=len(parsed_meta.tables),
            column_count=len(parsed_meta.columns),
            join_count=len(parsed_meta.joins),
            cte_count=len(parsed_meta.ctes),
            subquery_count=parsed_meta.subquery_count,
            aggregation_count=len(parsed_meta.aggregations),
            uses_effective_dating=parsed_meta.uses_effective_dating,
            uses_security_filter=parsed_meta.uses_security_filter,
            has_date_logic=bool(parsed_meta.date_conditions),
            has_business_logic=parsed_meta.has_business_logic,
            complexity_level=parsed_meta.complexity_level,
            complexity_score=parsed_meta.complexity_score,
            tables_json=json.dumps(parsed_meta.tables),
            columns_json=json.dumps(parsed_meta.columns),
            joins_json=json.dumps(parsed_meta.joins),
            filters_json=json.dumps(parsed_meta.filters),
            aggregations_json=json.dumps(parsed_meta.aggregations),
            date_conditions_json=json.dumps(parsed_meta.date_conditions),
            effective_dating_details=json.dumps(parsed_meta.effective_dating_details),
            security_filters_details=json.dumps(parsed_meta.security_filters_details),
            business_logic_details=json.dumps(parsed_meta.business_logic_details),
            parsed_at=datetime.datetime.utcnow()
        )
        session.add(metadata_record)

        # 5. Save Detected Parameters
        for p in parsed_meta.parameters:
            param_rec = SQLReportParameter(
                report_id=report.id,
                parameter_name=p["parameter_name"],
                parameter_type=p["parameter_type"],
                required=p["required"],
                default_value=p.get("default_value"),
                description=p.get("description")
            )
            session.add(param_rec)

        # 6. Save Initial Version Record (Never overwrite historical SQL)
        version_rec = SQLReportVersion(
            report_id=report.id,
            version_number=1,
            sql_query=sql_query.strip(),
            normalized_sql=normalized_sql,
            change_description="Initial report import from existing SQL.",
            changed_by_id=user.id if user else None,
            created_at=datetime.datetime.utcnow()
        )
        session.add(version_rec)

        # 7. Save Tags
        if tags:
            for t_name in tags:
                clean_tag = t_name.strip().lower()
                if not clean_tag:
                    continue
                tag_obj = session.query(Tag).filter(Tag.name == clean_tag).first()
                if not tag_obj:
                    tag_obj = Tag(name=clean_tag)
                    session.add(tag_obj)
                    session.flush()
                rel = SQLReportTag(report_id=report.id, tag_id=tag_obj.id)
                session.add(rel)

        # 8. Audit Log
        cls._log_action(
            session=session,
            user=user,
            action="SQL_IMPORTED",
            report_id=report.id,
            details=f"Imported report '{report.report_name}' ({report.report_code}) into database '{database_id}'."
        )

        session.commit()
        session.refresh(report)
        return report, dup_info

    # -------------------------------------------------------------
    # 3. File & Bulk File Imports
    # -------------------------------------------------------------
    @classmethod
    def import_sql_content(
        cls,
        session: Session,
        content: str,
        database_id: str,
        user: User,
        filename: Optional[str] = None,
        default_category: str = "Other"
    ) -> List[Tuple[SQLReport, Dict[str, Any]]]:
        """Parses .sql file content and imports all detected queries."""
        entries = SQLFileParser.parse_content(content, filename=filename)
        results = []
        for entry in entries:
            rep, dup = cls.create_report(
                session=session,
                report_name=entry.extracted_name or (filename or "Imported Query"),
                sql_query=entry.raw_sql,
                database_id=database_id,
                user=user,
                description=entry.extracted_description or "Imported from file.",
                business_purpose=entry.extracted_description or "",
                category=entry.extracted_category if entry.extracted_category != "Other" else default_category,
                tags=entry.extracted_tags
            )
            results.append((rep, dup))
        return results

    @classmethod
    def bulk_import(
        cls,
        session: Session,
        files_dict: Dict[str, str],  # {filename: content}
        database_id: str,
        user: User
    ) -> Dict[str, Any]:
        """Bulk imports multiple .sql files and generates diagnostic summary."""
        total_files = len(files_dict)
        imported_count = 0
        duplicate_count = 0
        invalid_count = 0
        details = []

        for fn, content in files_dict.items():
            file_entries = SQLFileParser.parse_content(content, filename=fn)
            if not file_entries:
                details.append({"filename": fn, "status": "EMPTY", "message": "No valid queries detected."})
                continue

            for entry in file_entries:
                rep, dup = cls.create_report(
                    session=session,
                    report_name=entry.extracted_name or fn,
                    sql_query=entry.raw_sql,
                    database_id=database_id,
                    user=user,
                    description=entry.extracted_description or f"Bulk imported from {fn}",
                    category=entry.extracted_category or "Other",
                    tags=entry.extracted_tags
                )

                status_label = "VALID"
                if dup["is_duplicate"]:
                    status_label = "DUPLICATE"
                    duplicate_count += 1
                elif not rep.is_valid:
                    status_label = "INVALID"
                    invalid_count += 1
                else:
                    imported_count += 1

                details.append({
                    "filename": fn,
                    "report_code": rep.report_code,
                    "report_name": rep.report_name,
                    "status": status_label,
                    "is_valid": rep.is_valid,
                    "is_duplicate": dup["is_duplicate"],
                    "complexity": rep.metadata_rel.complexity_level if rep.metadata_rel else "LOW",
                    "error": rep.validation_error
                })

        return {
            "total_files": total_files,
            "total_queries_processed": len(details),
            "imported_valid": imported_count,
            "duplicates_detected": duplicate_count,
            "invalid_queries": invalid_count,
            "details": details
        }

    # -------------------------------------------------------------
    # 4. Version Control & Updates
    # -------------------------------------------------------------
    @classmethod
    def update_report(
        cls,
        session: Session,
        report_id: int,
        user: User,
        report_name: Optional[str] = None,
        description: Optional[str] = None,
        business_purpose: Optional[str] = None,
        category: Optional[str] = None,
        sql_query: Optional[str] = None,
        change_description: str = "Updated report."
    ) -> SQLReport:
        """Updates report metadata, and if SQL changed, creates a new version record."""
        report = session.query(SQLReport).filter(SQLReport.id == report_id).first()
        if not report:
            raise KeyError(f"Report ID {report_id} not found.")

        if report_name:
            report.report_name = report_name.strip()
        if description:
            report.description = description.strip()
        if business_purpose:
            report.business_purpose = business_purpose.strip()
        if category:
            report.category = category.strip()

        # If SQL Query text was modified
        if sql_query and sql_query.strip() != report.sql_query.strip():
            dialect_rules = connection_manager.get_dialect_rules(report.database_id)
            dialect_name = dialect_rules.dialect_name if dialect_rules else "sqlite"

            new_norm, new_hash = SQLNormalizer.normalize(sql_query, dialect=dialect_name)
            parsed_meta = SQLParser.parse_query(sql_query, read_dialect=dialect_name)

            report.version += 1
            report.sql_query = sql_query.strip()
            report.normalized_sql = new_norm
            report.sql_hash = new_hash
            report.is_valid = parsed_meta.is_valid
            report.validation_error = parsed_meta.validation_error
            report.validated_at = datetime.datetime.utcnow()
            report.status = "PENDING_REVIEW" if parsed_meta.is_valid else "INVALID"

            # Create immutable version record
            ver_rec = SQLReportVersion(
                report_id=report.id,
                version_number=report.version,
                sql_query=sql_query.strip(),
                normalized_sql=new_norm,
                change_description=change_description,
                changed_by_id=user.id if user else None,
                created_at=datetime.datetime.utcnow()
            )
            session.add(ver_rec)

            # Update Metadata record
            meta_rec = report.metadata_rel
            if meta_rec:
                meta_rec.table_count = len(parsed_meta.tables)
                meta_rec.column_count = len(parsed_meta.columns)
                meta_rec.join_count = len(parsed_meta.joins)
                meta_rec.cte_count = len(parsed_meta.ctes)
                meta_rec.subquery_count = parsed_meta.subquery_count
                meta_rec.aggregation_count = len(parsed_meta.aggregations)
                meta_rec.uses_effective_dating = parsed_meta.uses_effective_dating
                meta_rec.uses_security_filter = parsed_meta.uses_security_filter
                meta_rec.has_date_logic = bool(parsed_meta.date_conditions)
                meta_rec.has_business_logic = parsed_meta.has_business_logic
                meta_rec.complexity_level = parsed_meta.complexity_level
                meta_rec.complexity_score = parsed_meta.complexity_score
                meta_rec.tables_json = json.dumps(parsed_meta.tables)
                meta_rec.columns_json = json.dumps(parsed_meta.columns)
                meta_rec.joins_json = json.dumps(parsed_meta.joins)
                meta_rec.filters_json = json.dumps(parsed_meta.filters)
                meta_rec.aggregations_json = json.dumps(parsed_meta.aggregations)
                meta_rec.date_conditions_json = json.dumps(parsed_meta.date_conditions)
                meta_rec.effective_dating_details = json.dumps(parsed_meta.effective_dating_details)
                meta_rec.security_filters_details = json.dumps(parsed_meta.security_filters_details)
                meta_rec.business_logic_details = json.dumps(parsed_meta.business_logic_details)
                meta_rec.parsed_at = datetime.datetime.utcnow()

            cls._log_action(
                session=session,
                user=user,
                action="SQL_VERSION_CREATED",
                report_id=report.id,
                details=f"Created version v{report.version} for '{report.report_name}'."
            )
        else:
            cls._log_action(
                session=session,
                user=user,
                action="SQL_UPDATED",
                report_id=report.id,
                details=f"Updated metadata for '{report.report_name}'."
            )

        report.updated_at = datetime.datetime.utcnow()
        session.commit()
        session.refresh(report)
        return report

    @classmethod
    def compare_versions(
        cls,
        session: Session,
        report_id: int,
        v1_num: int,
        v2_num: int
    ) -> Dict[str, Any]:
        """Generates unified diff comparison between two versions of an SQL report."""
        v1 = session.query(SQLReportVersion).filter(
            SQLReportVersion.report_id == report_id,
            SQLReportVersion.version_number == v1_num
        ).first()
        v2 = session.query(SQLReportVersion).filter(
            SQLReportVersion.report_id == report_id,
            SQLReportVersion.version_number == v2_num
        ).first()

        if not v1 or not v2:
            raise KeyError("One or both requested versions not found.")

        v1_lines = v1.sql_query.splitlines(keepends=True)
        v2_lines = v2.sql_query.splitlines(keepends=True)

        diff = list(difflib.unified_diff(
            v1_lines, v2_lines,
            fromfile=f"v{v1_num}",
            tofile=f"v{v2_num}"
        ))

        return {
            "report_id": report_id,
            "version_1": v1_num,
            "version_2": v2_num,
            "v1_created_at": v1.created_at.isoformat() if v1.created_at else "",
            "v2_created_at": v2.created_at.isoformat() if v2.created_at else "",
            "diff_text": "".join(diff),
            "diff_lines": [line.rstrip() for line in diff]
        }

    # -------------------------------------------------------------
    # 5. Approval, Rejection & Archiving Workflows
    # -------------------------------------------------------------
    @classmethod
    def approve_report(
        cls,
        session: Session,
        report_id: int,
        user: User,
        comment: str = "Approved for RAG knowledge repository."
    ) -> SQLReport:
        """Approves a validated report for active RAG knowledge use."""
        report = session.query(SQLReport).filter(SQLReport.id == report_id).first()
        if not report:
            raise KeyError(f"Report ID {report_id} not found.")

        if not report.is_valid:
            raise ValueError("Cannot approve an INVALID report. Syntax must be corrected first.")

        report.status = "APPROVED"
        report.updated_at = datetime.datetime.utcnow()

        approval = SQLApproval(
            report_id=report.id,
            action="APPROVE",
            user_id=user.id if user else None,
            comment=comment,
            created_at=datetime.datetime.utcnow()
        )
        session.add(approval)

        cls._log_action(
            session=session,
            user=user,
            action="SQL_APPROVED",
            report_id=report.id,
            details=f"Report '{report.report_name}' approved by {user.username if user else 'System'}."
        )

        session.commit()
        session.refresh(report)
        return report

    @classmethod
    def reject_report(
        cls,
        session: Session,
        report_id: int,
        user: User,
        reason: str
    ) -> SQLReport:
        """Rejects a report and resets its status."""
        report = session.query(SQLReport).filter(SQLReport.id == report_id).first()
        if not report:
            raise KeyError(f"Report ID {report_id} not found.")

        report.status = "REJECTED"
        report.updated_at = datetime.datetime.utcnow()

        approval = SQLApproval(
            report_id=report.id,
            action="REJECT",
            user_id=user.id if user else None,
            comment=reason,
            created_at=datetime.datetime.utcnow()
        )
        session.add(approval)

        cls._log_action(
            session=session,
            user=user,
            action="SQL_REJECTED",
            report_id=report.id,
            details=f"Report '{report.report_name}' rejected. Reason: {reason}"
        )

        session.commit()
        session.refresh(report)
        return report

    @classmethod
    def archive_report(
        cls,
        session: Session,
        report_id: int,
        user: User,
        reason: str = "Archived."
    ) -> SQLReport:
        """Archives a report, removing it from active RAG knowledge without deleting history."""
        report = session.query(SQLReport).filter(SQLReport.id == report_id).first()
        if not report:
            raise KeyError(f"Report ID {report_id} not found.")

        report.status = "ARCHIVED"
        report.updated_at = datetime.datetime.utcnow()

        approval = SQLApproval(
            report_id=report.id,
            action="ARCHIVE",
            user_id=user.id if user else None,
            comment=reason,
            created_at=datetime.datetime.utcnow()
        )
        session.add(approval)

        cls._log_action(
            session=session,
            user=user,
            action="SQL_ARCHIVED",
            report_id=report.id,
            details=f"Report '{report.report_name}' archived."
        )

        session.commit()
        session.refresh(report)
        return report

    # -------------------------------------------------------------
    # 6. RAG Knowledge Document Generation
    # -------------------------------------------------------------
    @classmethod
    def get_rag_knowledge_documents(
        cls,
        session: Session,
        organization_id: str = "org_default",
        database_id: Optional[str] = None
    ) -> List[SQLKnowledgeDocument]:
        """Extracts RAG-ready knowledge documents for all APPROVED reports."""
        q = session.query(SQLReport).filter(
            SQLReport.organization_id == organization_id,
            SQLReport.status == "APPROVED"
        )
        if database_id:
            q = q.filter(SQLReport.database_id == database_id)

        approved_reports = q.all()
        knowledge_docs = []
        for rep in approved_reports:
            doc = SQLKnowledgeBuilder.build_knowledge_document(rep, rep.metadata_rel)
            knowledge_docs.append(doc)
        return knowledge_docs

    # -------------------------------------------------------------
    # 7. Search & Advanced Filtering
    # -------------------------------------------------------------
    @classmethod
    def search_reports(
        cls,
        session: Session,
        query: Optional[str] = None,
        database_id: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        complexity: Optional[str] = None,
        uses_effective_dating: Optional[bool] = None,
        uses_security_filter: Optional[bool] = None,
        organization_id: str = "org_default",
        limit: int = 50
    ) -> List[SQLReport]:
        """Multi-facet search and filter across the repository."""
        q = session.query(SQLReport).outerjoin(SQLReportMetadata, SQLReport.id == SQLReportMetadata.report_id)
        q = q.filter(SQLReport.organization_id == organization_id)

        if database_id:
            q = q.filter(SQLReport.database_id == database_id)
        if category and category != "All":
            q = q.filter(SQLReport.category == category)
        if status and status != "All":
            q = q.filter(SQLReport.status == status)
        if complexity and complexity != "All":
            q = q.filter(SQLReportMetadata.complexity_level == complexity)
        if uses_effective_dating is not None:
            q = q.filter(SQLReportMetadata.uses_effective_dating == uses_effective_dating)
        if uses_security_filter is not None:
            q = q.filter(SQLReportMetadata.uses_security_filter == uses_security_filter)

        if query and query.strip():
            term = f"%{query.strip()}%"
            q = q.filter(
                or_(
                    SQLReport.report_name.ilike(term),
                    SQLReport.description.ilike(term),
                    SQLReport.business_purpose.ilike(term),
                    SQLReport.sql_query.ilike(term),
                    SQLReport.report_code.ilike(term),
                    SQLReportMetadata.tables_json.ilike(term),
                    SQLReportMetadata.columns_json.ilike(term)
                )
            )

        return q.order_by(SQLReport.updated_at.desc()).limit(limit).all()

    # -------------------------------------------------------------
    # 8. Dashboard Statistics
    # -------------------------------------------------------------
    @classmethod
    def get_dashboard_stats(
        cls,
        session: Session,
        organization_id: str = "org_default"
    ) -> Dict[str, Any]:
        """Calculates KPI statistics for the SQL Repository Dashboard."""
        base_q = session.query(SQLReport).filter(SQLReport.organization_id == organization_id)

        total_reports = base_q.count()
        approved_count = base_q.filter(SQLReport.status == "APPROVED").count()
        pending_count = base_q.filter(SQLReport.status == "PENDING_REVIEW").count()
        invalid_count = base_q.filter(SQLReport.status == "INVALID").count()
        archived_count = base_q.filter(SQLReport.status == "ARCHIVED").count()
        draft_count = base_q.filter(SQLReport.status == "DRAFT").count()

        # Category breakdown
        cat_counts = session.query(
            SQLReport.category, func.count(SQLReport.id)
        ).filter(SQLReport.organization_id == organization_id)\
         .group_by(SQLReport.category).all()
        by_category = [{"category": c[0], "count": c[1]} for c in cat_counts]

        # Database breakdown
        db_counts = session.query(
            SQLReport.database_id, func.count(SQLReport.id)
        ).filter(SQLReport.organization_id == organization_id)\
         .group_by(SQLReport.database_id).all()
        by_database = [{"database_id": d[0], "count": d[1]} for d in db_counts]

        # Complexity breakdown
        comp_counts = session.query(
            SQLReportMetadata.complexity_level, func.count(SQLReport.id)
        ).join(SQLReport, SQLReport.id == SQLReportMetadata.report_id)\
         .filter(SQLReport.organization_id == organization_id)\
         .group_by(SQLReportMetadata.complexity_level).all()
        by_complexity = [{"complexity": cp[0], "count": cp[1]} for cp in comp_counts]

        # Recent 5 reports
        recent = base_q.order_by(SQLReport.updated_at.desc()).limit(5).all()

        return {
            "total_reports": total_reports,
            "approved": approved_count,
            "pending_review": pending_count,
            "invalid": invalid_count,
            "archived": archived_count,
            "draft": draft_count,
            "by_category": by_category,
            "by_database": by_database,
            "by_complexity": by_complexity,
            "recent_reports": [
                {
                    "id": r.id,
                    "report_code": r.report_code,
                    "report_name": r.report_name,
                    "category": r.category,
                    "status": r.status,
                    "version": r.version,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else ""
                }
                for r in recent
            ]
        }

    # -------------------------------------------------------------
    # 9. Audit Logging Helper
    # -------------------------------------------------------------
    @classmethod
    def _log_action(
        cls,
        session: Session,
        user: Optional[User],
        action: str,
        report_id: Optional[int],
        details: str
    ):
        try:
            audit = AuditLog(
                user_id=user.id if user else None,
                username=user.username if user else "SYSTEM",
                user_role=user.role if user else "ADMIN",
                natural_query=f"[{action}] Report #{report_id}: {details}",
                generated_sql=None,
                execution_time_ms=0.0,
                row_count=0,
                status="SUCCESS",
                error_details=None,
                timestamp=datetime.datetime.utcnow()
            )
            session.add(audit)
        except Exception as e:
            print(f"[AuditLogger] Notice: {e}")
