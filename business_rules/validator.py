"""Module 4: Business Rule Validator.

Validates:
- SQL / Logical expression syntax using SQLGlot AST
- Allowed rule categories & priorities
- Referenced tables and columns against database schema allowlists
- Rule effective date validity ranges
- Security rule priority invariants
"""

import sqlglot
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend.database.models_schema import SchemaTable, SchemaColumn


VALID_RULE_TYPES = {
    "EMPLOYEE_STATUS", "EFFECTIVE_DATING", "SALARY", "ATTENDANCE", "LEAVE",
    "ATTRITION", "DEPARTMENT", "LOCATION", "JOB", "SECURITY", "DATA_ACCESS",
    "DATE", "CALCULATION", "FILTER", "AGGREGATION", "CUSTOM"
}

VALID_PRIORITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
VALID_SCOPES = {"GLOBAL", "DATABASE", "TABLE", "COLUMN", "REPORT", "DEPARTMENT", "ROLE"}


class RuleValidationError(ValueError):
    """Raised when a business rule fails syntactic or semantic validation."""
    pass


class RuleValidator:
    """Validates business rules against syntax, schema, and security invariants."""

    @classmethod
    def validate_rule(
        cls,
        rule_data: Dict[str, Any],
        db: Optional[Session] = None,
        database_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validates all aspects of a business rule.

        Raises:
            RuleValidationError: If any validation check fails.
        """
        name = rule_data.get("rule_name")
        if not name or len(name.strip()) < 2:
            raise RuleValidationError("Rule name is required and must be at least 2 characters.")

        rule_type = (rule_data.get("rule_type") or "").upper()
        if rule_type not in VALID_RULE_TYPES:
            raise RuleValidationError(
                f"Invalid rule type '{rule_type}'. Allowed types: {sorted(list(VALID_RULE_TYPES))}"
            )

        priority = (rule_data.get("priority") or "MEDIUM").upper()
        if priority not in VALID_PRIORITIES:
            raise RuleValidationError(
                f"Invalid priority '{priority}'. Allowed: {sorted(list(VALID_PRIORITIES))}"
            )

        expr = rule_data.get("rule_expression")
        if not expr or len(expr.strip()) < 2:
            raise RuleValidationError("Rule expression is required and cannot be empty.")

        # 1. Syntax Check via SQLGlot
        cls.validate_expression_syntax(expr)

        # 2. Date Range Check
        eff_from = rule_data.get("effective_from")
        eff_to = rule_data.get("effective_to")
        if eff_from and eff_to and eff_from > eff_to:
            raise RuleValidationError(
                f"Rule validity start date ({eff_from}) cannot be after end date ({eff_to})."
            )

        # 3. Security Rule Check
        if rule_type in ["SECURITY", "DATA_ACCESS"] and priority not in ["HIGH", "CRITICAL"]:
            raise RuleValidationError("Security rules must have priority HIGH or CRITICAL.")

        # 4. Schema Validation (if DB session provided)
        target_tbl = rule_data.get("table_name")
        target_col = rule_data.get("column_name")
        db_id = rule_data.get("database_id") or database_id or "sqlite_hr_default"

        if db and target_tbl:
            cls.validate_schema_references(db, db_id, target_tbl, target_col)

        return {
            "valid": True,
            "rule_type": rule_type,
            "priority": priority,
            "rule_expression": expr
        }

    @classmethod
    def validate_expression_syntax(cls, expression: str):
        """Ensures SQL/logical expression is well-formed using SQLGlot."""
        # Wrap expression into a mock WHERE clause for parsing
        test_sql = f"SELECT 1 WHERE {expression}"
        try:
            parsed = sqlglot.parse_one(test_sql)
            if not parsed:
                raise RuleValidationError(f"Could not parse SQL expression: '{expression}'")
        except Exception as e:
            raise RuleValidationError(f"Invalid SQL/logical expression syntax: '{expression}'. Details: {str(e)}")

    @classmethod
    def validate_schema_references(
        cls,
        db: Session,
        database_id: str,
        table_name: str,
        column_name: Optional[str] = None
    ):
        """Validates that referenced tables and columns exist in the discovered schema."""
        tbl = (
            db.query(SchemaTable)
            .filter(
                SchemaTable.database_id == database_id,
                SchemaTable.table_name.ilike(table_name)
            )
            .first()
        )
        if not tbl:
            raise RuleValidationError(
                f"Referenced table '{table_name}' does not exist in schema for database '{database_id}'."
            )

        if column_name:
            col = (
                db.query(SchemaColumn)
                .filter(
                    SchemaColumn.table_id == tbl.id,
                    SchemaColumn.column_name.ilike(column_name)
                )
                .first()
            )
            if not col:
                raise RuleValidationError(
                    f"Referenced column '{column_name}' does not exist in table '{table_name}'."
                )
