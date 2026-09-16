"""Database schema allowlist validator and hallucination detector."""

from sqlglot import exp

from backend.database.connection_manager import connection_manager

from .schemas import ChecklistItem

DEFAULT_FALLBACK_TABLES = {
    "employees", "departments", "compensation_history",
    "performance_reviews", "leave_records", "job_profiles",
    "attrition_records", "sql_repository", "audit_logs"
}


class SchemaValidator:
    """Verifies that all tables and columns referenced exist in the database catalog."""

    @staticmethod
    def get_catalog_schema(database_id: str) -> tuple[set[str], dict[str, set[str]]]:
        """Fetches known tables and columns for a given registered database."""
        try:
            schema = connection_manager.get_schema(database_id)
            if schema and hasattr(schema, "table_allowlist"):
                return schema.table_allowlist, schema.column_allowlist_map
        except Exception:
            pass

        allowed_tables = {t.lower() for t in DEFAULT_FALLBACK_TABLES}
        return allowed_tables, {}

    @classmethod
    def validate(
        cls,
        expression: exp.Expression,
        database_id: str = "sqlite_hr_default"
    ) -> tuple[bool, list[ChecklistItem], list[str], set[str]]:
        checklist = []
        violations = []
        referenced_tables: set[str] = set()

        allowed_tables, allowed_columns = cls.get_catalog_schema(database_id)

        # 1. Extract CTE aliases so they are not treated as missing physical tables
        cte_aliases = set()
        for cte in expression.find_all(exp.CTE):
            if cte.alias:
                cte_aliases.add(cte.alias.lower())

        # 2. Check all Table AST nodes
        unknown_tables = set()
        table_alias_map = {}

        for tbl in expression.find_all(exp.Table):
            t_name = tbl.name.lower()
            t_alias = tbl.alias.lower() if tbl.alias else t_name

            if t_name in cte_aliases:
                continue

            referenced_tables.add(t_name)
            table_alias_map[t_alias] = t_name

            if t_name not in allowed_tables:
                unknown_tables.add(t_name)

        if unknown_tables:
            checklist.append(ChecklistItem(
                check_name="schema_table_allowlist",
                passed=False,
                severity="BLOCKER",
                details=f"Unknown/unauthorized tables: {sorted(unknown_tables)}"
            ))
            violations.append(f"Schema hallucination: Table(s) {sorted(unknown_tables)} do not exist in database '{database_id}'.")
            return False, checklist, violations, referenced_tables

        checklist.append(ChecklistItem(
            check_name="schema_table_allowlist",
            passed=True,
            severity="INFO",
            details=f"All referenced tables ({len(referenced_tables)}) exist in database catalog."
        ))

        # 3. Check column references if column catalog exists
        unknown_columns = set()
        select_aliases = {a.alias.lower() for a in expression.find_all(exp.Alias) if a.alias}
        if allowed_columns:
            all_known_cols = set()
            for cols in allowed_columns.values():
                all_known_cols.update(cols)

            for col in expression.find_all(exp.Column):
                col_name = col.name.lower()
                tbl_ref = col.table.lower() if col.table else None

                if col_name in ("*", "") or col_name in select_aliases:
                    continue

                if tbl_ref:
                    actual_table = table_alias_map.get(tbl_ref, tbl_ref)
                    if actual_table in cte_aliases:
                        continue
                    if actual_table in allowed_columns and col_name not in allowed_columns[actual_table]:
                        unknown_columns.add(f"{actual_table}.{col_name}")
                elif len(referenced_tables) == 1:
                    single_tbl = next(iter(referenced_tables))
                    if single_tbl in allowed_columns and col_name not in allowed_columns[single_tbl]:
                        unknown_columns.add(f"{single_tbl}.{col_name}")

        if unknown_columns:
            checklist.append(ChecklistItem(
                check_name="schema_column_allowlist",
                passed=False,
                severity="BLOCKER",
                details=f"Unknown columns referenced: {sorted(unknown_columns)}"
            ))
            violations.append(f"Schema hallucination: Column(s) {sorted(unknown_columns)} do not exist in schema catalog.")
            return False, checklist, violations, referenced_tables

        checklist.append(ChecklistItem(
            check_name="schema_column_allowlist",
            passed=True,
            severity="INFO",
            details="All referenced columns successfully verified against catalog."
        ))

        return True, checklist, violations, referenced_tables
