"""Module 4: Business Rule Service Layer.

Orchestrates:
- Rule creation with unique codes and initial version snapshots
- Rule editing with automatic immutable versioning for active rules
- Approval & Rejection workflows with audit trails
- Conflict and duplicate detection
- SQL-derived candidate rule detection
- Active rule filtering for Module 5 RAG
"""

import datetime
import logging
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend.database.models_repo import SQLReport
from backend.database.models_rules import (
    BusinessRule,
    BusinessRuleAudit,
    BusinessRuleVersion,
    RuleColumn,
    RuleTable,
)

from .validator import RuleValidator

logger = logging.getLogger("business_rules.service")


class BusinessRuleService:
    """Core domain service for managing enterprise HR business rules."""

    def __init__(self, db: Session):
        self.db = db

    def create_rule(
        self,
        data: dict[str, Any],
        user_name: str = "admin"
    ) -> BusinessRule:
        """Validates and creates a new business rule with version 1 and audit log."""
        # 1. Validate rule data
        RuleValidator.validate_rule(data, db=self.db, database_id=data.get("database_id"))

        # 2. Generate unique rule code
        rule_type = (data.get("rule_type") or "FILTER").upper()
        prefix = self._get_prefix_for_type(rule_type)
        rule_code = self._generate_rule_code(prefix)

        # 3. Instantiate Rule
        rule = BusinessRule(
            rule_code=rule_code,
            rule_name=data["rule_name"],
            description=data.get("description"),
            rule_type=rule_type,
            rule_expression=data["rule_expression"],
            natural_language_rule=data["natural_language_rule"],
            source_type=data.get("source_type", "ADMIN_CREATED"),
            source_report_id=data.get("source_report_id"),
            source_sql_report=data.get("source_sql_report"),
            source_sql_expression=data.get("source_sql_expression"),
            status=data.get("status", "DRAFT"),
            priority=(data.get("priority") or "MEDIUM").upper(),
            mandatory=bool(data.get("mandatory", False)),
            scope=(data.get("scope") or "TABLE").upper(),
            database_id=data.get("database_id", "sqlite_hr_default"),
            table_name=data.get("table_name"),
            column_name=data.get("column_name"),
            confidence_score=float(data.get("confidence_score", 1.0)),
            created_by=user_name,
            effective_from=data.get("effective_from"),
            effective_to=data.get("effective_to"),
            version=1,
            is_current=True
        )
        self.db.add(rule)
        self.db.flush()

        # 4. Create Initial Version Snapshot
        version_rec = BusinessRuleVersion(
            rule_id=rule.id,
            version_number=1,
            rule_name=rule.rule_name,
            description=rule.description,
            rule_expression=rule.rule_expression,
            natural_language_rule=rule.natural_language_rule,
            rule_type=rule.rule_type,
            status=rule.status,
            changed_by=user_name,
            change_reason="Initial rule creation.",
            is_current=True
        )
        self.db.add(version_rec)

        # 5. Log Audit Record
        audit_rec = BusinessRuleAudit(
            rule_id=rule.id,
            action="CREATE",
            old_value=None,
            new_value={"expression": rule.rule_expression, "status": rule.status},
            performed_by=user_name,
            reason="Rule created."
        )
        self.db.add(audit_rec)

        # 6. Map Tables and Columns if provided
        if rule.table_name:
            self.db.add(RuleTable(rule_id=rule.id, table_name=rule.table_name))
            if rule.column_name:
                self.db.add(RuleColumn(rule_id=rule.id, table_name=rule.table_name, column_name=rule.column_name))

        self.db.commit()
        self.db.refresh(rule)
        return rule

    def update_rule(
        self,
        rule_id: int,
        data: dict[str, Any],
        user_name: str = "admin"
    ) -> BusinessRule:
        """Updates a rule. If the rule is ACTIVE, creates a new immutable version."""
        rule = self.db.query(BusinessRule).filter_by(id=rule_id).first()
        if not rule:
            raise ValueError(f"Business rule with ID {rule_id} not found.")

        old_state = {
            "name": rule.rule_name,
            "expression": rule.rule_expression,
            "nl": rule.natural_language_rule,
            "status": rule.status,
            "version": rule.version
        }

        # Check if active - requires version increment
        is_active = (rule.status == "ACTIVE")
        change_reason = data.get("change_reason", "Rule definition updated.")

        # Update fields
        for field in ["rule_name", "description", "rule_type", "rule_expression",
                      "natural_language_rule", "priority", "mandatory", "scope",
                      "table_name", "column_name", "effective_from", "effective_to"]:
            if field in data and data[field] is not None:
                setattr(rule, field, data[field])

        # Re-validate
        RuleValidator.validate_rule(
            {
                "rule_name": rule.rule_name,
                "rule_type": rule.rule_type,
                "rule_expression": rule.rule_expression,
                "natural_language_rule": rule.natural_language_rule,
                "priority": rule.priority,
                "effective_from": rule.effective_from,
                "effective_to": rule.effective_to,
                "table_name": rule.table_name,
                "column_name": rule.column_name,
                "database_id": rule.database_id
            },
            db=self.db,
            database_id=rule.database_id
        )

        rule.updated_by = user_name
        rule.updated_at = datetime.datetime.utcnow()

        if is_active:
            # Create a new version
            rule.version += 1

            # Mark previous versions is_current = False
            for v in rule.versions:
                v.is_current = False

            new_version = BusinessRuleVersion(
                rule_id=rule.id,
                version_number=rule.version,
                rule_name=rule.rule_name,
                description=rule.description,
                rule_expression=rule.rule_expression,
                natural_language_rule=rule.natural_language_rule,
                rule_type=rule.rule_type,
                status=rule.status,
                changed_by=user_name,
                change_reason=change_reason,
                is_current=True
            )
            self.db.add(new_version)

            audit_action = "VERSION_CREATE"
        else:
            audit_action = "EDIT"

        # Log audit
        audit_rec = BusinessRuleAudit(
            rule_id=rule.id,
            action=audit_action,
            old_value=old_state,
            new_value={"expression": rule.rule_expression, "version": rule.version},
            performed_by=user_name,
            reason=change_reason
        )
        self.db.add(audit_rec)

        self.db.commit()
        self.db.refresh(rule)
        return rule

    def approve_rule(
        self,
        rule_id: int,
        comment: str,
        user_name: str = "admin"
    ) -> BusinessRule:
        """Approves a detected or draft rule into ACTIVE status."""
        rule = self.db.query(BusinessRule).filter_by(id=rule_id).first()
        if not rule:
            raise ValueError(f"Business rule ID {rule_id} not found.")

        if rule.status == "REJECTED":
            raise ValueError("Cannot approve a rejected rule directly. Create a new rule or re-submit.")

        old_status = rule.status
        rule.status = "ACTIVE"
        rule.approved_by = user_name
        rule.approved_at = datetime.datetime.utcnow()
        rule.approval_comment = comment

        # Update current version status
        curr_ver = next((v for v in rule.versions if v.is_current), None)
        if curr_ver:
            curr_ver.status = "ACTIVE"

        audit_rec = BusinessRuleAudit(
            rule_id=rule.id,
            action="APPROVE",
            old_value={"status": old_status},
            new_value={"status": "ACTIVE", "approved_by": user_name},
            performed_by=user_name,
            reason=comment
        )
        self.db.add(audit_rec)

        self.db.commit()
        self.db.refresh(rule)
        return rule

    def reject_rule(
        self,
        rule_id: int,
        reason: str,
        user_name: str = "admin"
    ) -> BusinessRule:
        """Rejects a rule. Preserves the rule record for compliance and auditing."""
        rule = self.db.query(BusinessRule).filter_by(id=rule_id).first()
        if not rule:
            raise ValueError(f"Business rule ID {rule_id} not found.")

        if not reason or len(reason.strip()) < 3:
            raise ValueError("Rejection reason is mandatory.")

        old_status = rule.status
        rule.status = "REJECTED"
        rule.rejection_reason = reason

        curr_ver = next((v for v in rule.versions if v.is_current), None)
        if curr_ver:
            curr_ver.status = "REJECTED"

        audit_rec = BusinessRuleAudit(
            rule_id=rule.id,
            action="REJECT",
            old_value={"status": old_status},
            new_value={"status": "REJECTED", "reason": reason},
            performed_by=user_name,
            reason=reason
        )
        self.db.add(audit_rec)

        self.db.commit()
        self.db.refresh(rule)
        return rule

    def activate_rule(
        self,
        rule_id: int,
        user_name: str = "admin"
    ) -> BusinessRule:
        """Activates an approved rule after verifying dependency health."""
        rule = self.db.query(BusinessRule).filter_by(id=rule_id).first()
        if not rule:
            raise ValueError(f"Business rule ID {rule_id} not found.")

        # Check dependencies
        for dep in rule.dependencies:
            dep_rule = self.db.query(BusinessRule).filter_by(id=dep.depends_on_rule_id).first()
            if not dep_rule or dep_rule.status != "ACTIVE":
                raise ValueError(
                    f"Cannot activate rule: Dependency '{dep_rule.rule_name if dep_rule else dep.depends_on_rule_id}' is not ACTIVE."
                )

        rule.status = "ACTIVE"
        self.db.add(BusinessRuleAudit(
            rule_id=rule.id,
            action="ACTIVATE",
            new_value={"status": "ACTIVE"},
            performed_by=user_name,
            reason="Activated by admin."
        ))
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def deactivate_rule(
        self,
        rule_id: int,
        user_name: str = "admin"
    ) -> BusinessRule:
        """Deactivates a rule, preventing it from appearing in active RAG retrieval."""
        rule = self.db.query(BusinessRule).filter_by(id=rule_id).first()
        if not rule:
            raise ValueError(f"Business rule ID {rule_id} not found.")

        rule.status = "INACTIVE"
        self.db.add(BusinessRuleAudit(
            rule_id=rule.id,
            action="DEACTIVATE",
            new_value={"status": "INACTIVE"},
            performed_by=user_name,
            reason="Deactivated by admin."
        ))
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def get_active_rules(self, database_id: str = "sqlite_hr_default") -> list[BusinessRule]:
        """Returns ONLY active, current, approved business rules for Module 5 RAG."""
        return (
            self.db.query(BusinessRule)
            .filter(
                BusinessRule.database_id == database_id,
                BusinessRule.status == "ACTIVE",
                BusinessRule.is_current == True
            )
            .order_by(BusinessRule.priority.asc(), BusinessRule.rule_code.asc())
            .all()
        )

    def get_rules(
        self,
        database_id: str = "sqlite_hr_default",
        status: str | None = None,
        rule_type: str | None = None,
        priority: str | None = None,
        table_name: str | None = None,
        mandatory: bool | None = None,
        search: str | None = None
    ) -> list[BusinessRule]:
        """Lists rules with comprehensive filtering."""
        query = self.db.query(BusinessRule).filter(
            BusinessRule.database_id == database_id,
            BusinessRule.is_current == True
        )
        if status and status.upper() != "ALL":
            query = query.filter(BusinessRule.status == status.upper())
        if rule_type and rule_type.upper() != "ALL":
            query = query.filter(BusinessRule.rule_type == rule_type.upper())
        if priority and priority.upper() != "ALL":
            query = query.filter(BusinessRule.priority == priority.upper())
        if table_name and table_name.strip():
            query = query.filter(BusinessRule.table_name.ilike(f"%{table_name}%"))
        if mandatory is not None:
            query = query.filter(BusinessRule.mandatory == mandatory)
        if search:
            term = f"%{search}%"
            query = query.filter(
                or_(
                    BusinessRule.rule_code.ilike(term),
                    BusinessRule.rule_name.ilike(term),
                    BusinessRule.rule_expression.ilike(term),
                    BusinessRule.natural_language_rule.ilike(term),
                    BusinessRule.description.ilike(term)
                )
            )

        return query.order_by(BusinessRule.created_at.desc()).all()

    def get_rule_detail(self, rule_id: int) -> dict[str, Any] | None:
        """Returns detailed rule information including versions, audits, and dependencies."""
        rule = self.db.query(BusinessRule).filter_by(id=rule_id).first()
        if not rule:
            return None

        versions = [
            {
                "version_number": v.version_number,
                "rule_name": v.rule_name,
                "expression": v.rule_expression,
                "natural_language": v.natural_language_rule,
                "status": v.status,
                "changed_by": v.changed_by,
                "change_reason": v.change_reason,
                "is_current": v.is_current,
                "created_at": v.created_at.isoformat() if v.created_at else None
            }
            for v in sorted(rule.versions, key=lambda x: x.version_number, reverse=True)
        ]

        audits = [
            {
                "action": a.action,
                "performed_by": a.performed_by,
                "performed_at": a.performed_at.isoformat() if a.performed_at else None,
                "reason": a.reason,
                "old_value": a.old_value,
                "new_value": a.new_value
            }
            for a in sorted(rule.audits, key=lambda x: x.performed_at, reverse=True)
        ]

        return {
            "id": rule.id,
            "rule_code": rule.rule_code,
            "rule_name": rule.rule_name,
            "description": rule.description,
            "rule_type": rule.rule_type,
            "rule_expression": rule.rule_expression,
            "natural_language_rule": rule.natural_language_rule,
            "source_type": rule.source_type,
            "source_report_id": rule.source_report_id,
            "source_sql_report": rule.source_sql_report,
            "status": rule.status,
            "priority": rule.priority,
            "mandatory": rule.mandatory,
            "scope": rule.scope,
            "database_id": rule.database_id,
            "table_name": rule.table_name,
            "column_name": rule.column_name,
            "confidence_score": rule.confidence_score,
            "version": rule.version,
            "is_current": rule.is_current,
            "created_by": rule.created_by,
            "created_at": rule.created_at.isoformat() if rule.created_at else None,
            "approved_by": rule.approved_by,
            "approved_at": rule.approved_at.isoformat() if rule.approved_at else None,
            "approval_comment": rule.approval_comment,
            "rejection_reason": rule.rejection_reason,
            "versions": versions,
            "audit_trail": audits
        }

    def detect_rules_from_sql_repository(self, database_id: str = "sqlite_hr_default") -> list[BusinessRule]:
        """Mines Module 2's SQL reports to discover candidate business rules."""
        reports = self.db.query(SQLReport).filter_by(database_id=database_id).all()
        detected_rules = []

        for r in reports:
            meta = r.metadata_rel
            if not meta:
                continue

            # 1. Effective dating rule detection
            if meta.uses_effective_dating:
                rule_name = f"Effective Dating Rule ({r.report_name})"
                expr = "CURRENT_DATE BETWEEN effective_start_date AND effective_end_date"
                cand_data = {
                    "rule_name": rule_name,
                    "rule_type": "EFFECTIVE_DATING",
                    "rule_expression": expr,
                    "natural_language_rule": "Records must be valid on the current transaction date.",
                    "source_type": "SQL_DETECTED",
                    "source_report_id": str(r.id),
                    "source_sql_report": r.report_name,
                    "status": "DETECTED",
                    "priority": "HIGH",
                    "mandatory": True,
                    "scope": "TABLE",
                    "database_id": database_id,
                    "table_name": "employees",
                    "confidence_score": 0.95
                }
                if not self._rule_exists(database_id, expr):
                    detected_rules.append(self.create_rule(cand_data, user_name="system_detector"))

            # 2. Check filters for common status rules
            filters = meta.filters if hasattr(meta, "filters") and isinstance(meta.filters, list) else []
            for f in filters:
                f_str = str(f).lower()
                if "status" in f_str and "active" in f_str:
                    expr = "employees.status = 'ACTIVE'"
                    cand_data = {
                        "rule_name": "Active Employee Rule",
                        "rule_type": "EMPLOYEE_STATUS",
                        "rule_expression": expr,
                        "natural_language_rule": "An employee is active when employment status equals ACTIVE.",
                        "source_type": "SQL_DETECTED",
                        "source_report_id": str(r.id),
                        "source_sql_report": r.report_name,
                        "status": "DETECTED",
                        "priority": "HIGH",
                        "mandatory": True,
                        "scope": "TABLE",
                        "database_id": database_id,
                        "table_name": "employees",
                        "column_name": "status",
                        "confidence_score": 0.99
                    }
                    if not self._rule_exists(database_id, expr):
                        detected_rules.append(self.create_rule(cand_data, user_name="system_detector"))

        return detected_rules

    def get_dashboard_stats(self, database_id: str = "sqlite_hr_default") -> dict[str, Any]:
        """Computes summary KPI statistics for the business rules dashboard."""
        query = self.db.query(BusinessRule).filter(
            BusinessRule.database_id == database_id,
            BusinessRule.is_current == True
        )
        all_rules = query.all()

        total = len(all_rules)
        active = sum(1 for r in all_rules if r.status == "ACTIVE")
        review = sum(1 for r in all_rules if r.status in ["DETECTED", "UNDER_REVIEW"])
        rejected = sum(1 for r in all_rules if r.status == "REJECTED")
        low_conf = sum(1 for r in all_rules if r.confidence_score < 0.70)
        mandatory = sum(1 for r in all_rules if r.mandatory)

        return {
            "total_rules": total,
            "active_rules": active,
            "rules_under_review": review,
            "rejected_rules": rejected,
            "low_confidence_rules": low_conf,
            "mandatory_rules": mandatory
        }

    def _rule_exists(self, database_id: str, expr: str) -> bool:
        """Checks if a rule with identical expression already exists."""
        return self.db.query(BusinessRule).filter(
            BusinessRule.database_id == database_id,
            BusinessRule.rule_expression == expr,
            BusinessRule.is_current == True
        ).first() is not None

    def _generate_rule_code(self, prefix: str) -> str:
        """Generates sequential rule codes e.g. BR-EMP-001."""
        count = self.db.query(func.count(BusinessRule.id)).scalar() or 0
        return f"BR-{prefix}-{str(count + 1).zfill(3)}"

    def _get_prefix_for_type(self, rule_type: str) -> str:
        prefixes = {
            "EMPLOYEE_STATUS": "EMP",
            "EFFECTIVE_DATING": "EFF",
            "SALARY": "SAL",
            "ATTENDANCE": "ATT",
            "LEAVE": "LEV",
            "ATTRITION": "ATT",
            "DEPARTMENT": "DEP",
            "SECURITY": "SEC",
            "DATA_ACCESS": "ACC",
            "CALCULATION": "CAL",
            "FILTER": "FLT",
            "AGGREGATION": "AGG",
        }
        return prefixes.get(rule_type, "GEN")
