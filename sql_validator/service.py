"""Central SQL Validator & Security Engine Service (Module 7)."""

import datetime
import hashlib
import json
import uuid

from sqlalchemy.orm import Session

from backend.auth.authorization import AuthorizationService
from backend.database.models import User
from backend.database.models_validation import SQLValidationAuditLog

from .business_rule_validator import BusinessRuleValidator
from .column_validator import ColumnValidator
from .complexity import ComplexityAnalyzer
from .join_validator import JoinValidator
from .parser import SQLValidatorParser
from .policy_engine import DEFAULT_POLICY
from .risk_engine import RiskEngine
from .schema_validator import SchemaValidator
from .schemas import (
    ChecklistItem,
    ComplexityMetrics,
    SQLValidationRequest,
    SQLValidationResponse,
    ValidationPolicy,
)
from .security_validator import SecurityValidator
from .statement_validator import StatementValidator


class SQLValidatorService:
    """Zero-trust AST validation gatekeeper between AI/Users and Execution Engine."""

    def __init__(self, db: Session, policy: ValidationPolicy | None = None):
        self.db = db
        self.policy = policy or DEFAULT_POLICY

    def validate_query(self, request: SQLValidationRequest) -> SQLValidationResponse:
        """
        Executes full zero-trust validation pipeline on requested SQL.
        HARD INVARIANT: NEVER executes the SQL query.
        """
        all_checklist: list[ChecklistItem] = []
        all_violations: list[str] = []
        all_warnings: list[str] = []
        referenced_tables: set[str] = set()

        raw_sql = request.sql.strip() if request.sql else ""
        sanitized_sql = raw_sql

        # 1. User & Database Authorization check (Module 11 integration)
        user = None
        if request.user_id:
            user = self.db.query(User).filter(User.id == request.user_id).first()
        elif request.username:
            user = self.db.query(User).filter(User.username == request.username).first()

        user_role = user.role if user else (request.user_role or "hr_analyst")

        # Check database tenant access
        if user:
            can_access = AuthorizationService.can_access_database(
                db=self.db,
                user=user,
                database_id=request.database_id,
                mode="read"
            )
            if not can_access:
                all_violations.append(f"Access Denied: User '{user.username}' lacks permission to access database '{request.database_id}'.")
                all_checklist.append(ChecklistItem(
                    check_name="database_authorization",
                    passed=False,
                    severity="BLOCKER",
                    details=f"User unauthorized for database '{request.database_id}'"
                ))
            else:
                all_checklist.append(ChecklistItem(
                    check_name="database_authorization",
                    passed=True,
                    severity="INFO",
                    details=f"Cleared to access database '{request.database_id}'"
                ))

        # 2. Syntax & AST Parsing
        parse_result = SQLValidatorParser.parse(raw_sql)
        if not parse_result.is_valid_syntax:
            all_checklist.append(ChecklistItem(
                check_name="syntax_validity",
                passed=False,
                severity="BLOCKER",
                details=str(parse_result.syntax_error)
            ))
            all_violations.append(f"Syntax Error: {parse_result.syntax_error}")
            return self._build_rejected_response(
                raw_sql=raw_sql,
                request=request,
                checklist=all_checklist,
                violations=all_violations,
                warnings=all_warnings,
                user=user,
                user_role=user_role
            )

        # 3. Statement Structure & Read-Only Check
        ok_stmt, stmt_checks, stmt_viols = StatementValidator.validate(parse_result)
        all_checklist.extend(stmt_checks)
        all_violations.extend(stmt_viols)
        if not ok_stmt:
            return self._build_rejected_response(
                raw_sql=raw_sql,
                request=request,
                checklist=all_checklist,
                violations=all_violations,
                warnings=all_warnings,
                user=user,
                user_role=user_role
            )

        root_expr = parse_result.expression

        # 4. Security & Dangerous Functions Check
        ok_sec, sanitized_sql, sec_checks, sec_viols, sec_warns = SecurityValidator.validate(
            raw_sql=raw_sql,
            expression=root_expr,
            disallow_comments=self.policy.disallow_comments
        )
        all_checklist.extend(sec_checks)
        all_violations.extend(sec_viols)
        all_warnings.extend(sec_warns)
        if not ok_sec:
            return self._build_rejected_response(
                raw_sql=raw_sql,
                request=request,
                checklist=all_checklist,
                violations=all_violations,
                warnings=all_warnings,
                user=user,
                user_role=user_role
            )

        # 5. Schema Allowlists & Hallucination Detection
        ok_schema, schema_checks, schema_viols, ref_tables = SchemaValidator.validate(
            expression=root_expr,
            database_id=request.database_id
        )
        referenced_tables.update(ref_tables)
        all_checklist.extend(schema_checks)
        all_violations.extend(schema_viols)
        if not ok_schema:
            return self._build_rejected_response(
                raw_sql=raw_sql,
                request=request,
                checklist=all_checklist,
                violations=all_violations,
                warnings=all_warnings,
                user=user,
                user_role=user_role
            )

        # 6. Column-Level Security (CLS) and SELECT * Policy
        allow_star = request.allow_select_star or self.policy.allow_select_star
        _, star_checks, star_viols, star_warns = ColumnValidator.validate_select_star(
            expression=root_expr,
            allow_select_star=allow_star
        )
        all_checklist.extend(star_checks)
        all_violations.extend(star_viols)
        all_warnings.extend(star_warns)

        ok_cls, cls_checks, cls_viols = ColumnValidator.validate_column_permissions(
            expression=root_expr,
            db=self.db,
            user=user,
            database_id=request.database_id,
            referenced_tables=referenced_tables
        )
        all_checklist.extend(cls_checks)
        all_violations.extend(cls_viols)
        if not ok_cls:
            return self._build_rejected_response(
                raw_sql=raw_sql,
                request=request,
                checklist=all_checklist,
                violations=all_violations,
                warnings=all_warnings,
                user=user,
                user_role=user_role
            )

        # 7. Joins & Cartesian Product Check
        ok_join, join_checks, join_viols, join_warns = JoinValidator.validate(
            expression=root_expr,
            max_joins=self.policy.max_joins,
            disallow_cartesian=self.policy.disallow_cartesian
        )
        all_checklist.extend(join_checks)
        all_violations.extend(join_viols)
        all_warnings.extend(join_warns)
        if not ok_join:
            return self._build_rejected_response(
                raw_sql=raw_sql,
                request=request,
                checklist=all_checklist,
                violations=all_violations,
                warnings=all_warnings,
                user=user,
                user_role=user_role
            )

        # 8. Business Rule Compliance (Effective Dating, etc.)
        _, br_checks, br_viols, br_warns = BusinessRuleValidator.validate(
            expression=root_expr,
            db=self.db,
            database_id=request.database_id,
            referenced_tables=referenced_tables
        )
        all_checklist.extend(br_checks)
        all_violations.extend(br_viols)
        all_warnings.extend(br_warns)

        # 9. Complexity & Risk Scoring
        complexity = ComplexityAnalyzer.analyze(root_expr)
        has_where = bool(root_expr.args.get("where"))
        has_limit = bool(root_expr.args.get("limit"))

        risk_score, risk_level, status = RiskEngine.calculate_risk(
            violations=all_violations,
            warnings=all_warnings,
            complexity=complexity,
            referenced_tables=referenced_tables,
            has_where=has_where,
            has_limit=has_limit,
            user_role=user_role,
            max_risk_score_auto_approval=self.policy.max_risk_score_auto_approval
        )

        # Compute SHA-256 hash
        sql_hash = hashlib.sha256(sanitized_sql.encode("utf-8")).hexdigest()

        # Issue validation token if approved
        validation_id = None
        expires_at_dt = None
        expires_at_str = None
        can_execute = False

        if status == "APPROVED":
            validation_id = f"val_{uuid.uuid4().hex}"
            now = datetime.datetime.now(datetime.UTC)
            expires_at_dt = now + datetime.timedelta(minutes=self.policy.token_ttl_minutes)
            expires_at_str = expires_at_dt.isoformat()
            can_execute = True
        else:
            now = datetime.datetime.now(datetime.UTC)
            expires_at_dt = now + datetime.timedelta(minutes=self.policy.token_ttl_minutes)

        # Record validation audit log
        audit_entry = SQLValidationAuditLog(
            validation_id=validation_id or f"rej_{uuid.uuid4().hex}",
            database_id=request.database_id,
            user_id=user.id if user else None,
            username=user.username if user else request.username,
            user_role=user_role,
            raw_sql=raw_sql,
            sanitized_sql=sanitized_sql,
            sql_hash=sql_hash,
            status=status,
            risk_score=risk_score,
            risk_level=risk_level,
            rules_checked=json.dumps([c.model_dump() for c in all_checklist]),
            violations=json.dumps(all_violations),
            warnings=json.dumps(all_warnings),
            expires_at=expires_at_dt,
            created_at=datetime.datetime.now(datetime.UTC)
        )
        try:
            self.db.add(audit_entry)
            self.db.commit()
        except Exception:
            self.db.rollback()

        return SQLValidationResponse(
            validation_id=validation_id,
            status=status,
            is_valid=(status == "APPROVED"),
            safe_error_explanation=None,
            risk_score=risk_score,
            risk_level=risk_level,
            sanitized_sql=sanitized_sql,
            sql_hash=sql_hash,
            expires_at=expires_at_str,
            checklist=all_checklist,
            violations=all_violations,
            warnings=all_warnings,
            complexity_metrics=complexity,
            can_execute=can_execute,
            timeout_seconds=30,
            max_row_limit=5000
        )

    def _build_rejected_response(
        self,
        raw_sql: str,
        request: SQLValidationRequest,
        checklist: list[ChecklistItem],
        violations: list[str],
        warnings: list[str],
        user: User | None,
        user_role: str
    ) -> SQLValidationResponse:
        """Helper to create a standard rejected response and log it."""
        sql_hash = hashlib.sha256(raw_sql.encode("utf-8")).hexdigest()
        now = datetime.datetime.now(datetime.UTC)
        expires_at = now + datetime.timedelta(minutes=15)

        # Record audit log
        audit = SQLValidationAuditLog(
            validation_id=f"rej_{uuid.uuid4().hex}",
            database_id=request.database_id,
            user_id=user.id if user else None,
            username=user.username if user else request.username,
            user_role=user_role,
            raw_sql=raw_sql,
            sanitized_sql=raw_sql,
            sql_hash=sql_hash,
            status="REJECTED",
            risk_score=100.0,
            risk_level="CRITICAL",
            rules_checked=json.dumps([c.model_dump() for c in checklist]),
            violations=json.dumps(violations),
            warnings=json.dumps(warnings),
            expires_at=expires_at,
            created_at=now
        )
        try:
            self.db.add(audit)
            self.db.commit()
        except Exception:
            self.db.rollback()

        safe_explanation = "; ".join(violations) if violations else "Query rejected due to security policy violations."

        return SQLValidationResponse(
            validation_id=None,
            status="REJECTED",
            is_valid=False,
            safe_error_explanation=safe_explanation,
            risk_score=100.0,
            risk_level="CRITICAL",
            sanitized_sql=raw_sql,
            sql_hash=sql_hash,
            expires_at=None,
            checklist=checklist,
            violations=violations,
            warnings=warnings,
            complexity_metrics=ComplexityMetrics(),
            can_execute=False,
            timeout_seconds=30,
            max_row_limit=5000
        )
