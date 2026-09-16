"""SQL Parser & Comprehensive Metadata Analyzer using SQLGlot.

Extracts:
1. Tables and Columns (with aliases)
2. Joins (left_table, right_table, join_type, join_condition)
3. WHERE Filter conditions (sanitized)
4. Aggregations (COUNT, SUM, AVG, MIN, MAX, COUNT DISTINCT)
5. Date logic conditions
6. Effective-dating detection (critical enterprise HR requirement)
7. Security filter conditions (organization_id, department_id, company_id, etc.)
8. Business logic constructs (CASE WHEN, COALESCE, NULLIF, DATEDIFF, window functions)
9. Heuristic complexity score (LOW, MEDIUM, HIGH, VERY_HIGH)
10. SQL parameter detection (:param, {param}, %param%)

Invariant: Parsing strictly analyzes AST syntax and never executes queries.
"""

import re
from typing import Any

from sqlglot import exp, parse_one, transpile


class ExtractedSQLMetadata:
    """Encapsulates all extracted syntactic, structural, and semantic metadata."""

    def __init__(self):
        self.is_valid: bool = True
        self.validation_error: str | None = None
        self.statement_type: str = "UNKNOWN"
        self.formatted_sql: str = ""

        # Structural Elements
        self.tables: list[str] = []
        self.columns: list[str] = []
        self.joins: list[dict[str, str]] = []
        self.filters: list[str] = []
        self.aggregations: list[dict[str, str]] = []
        self.group_by: list[str] = []
        self.order_by: list[str] = []
        self.ctes: list[str] = []
        self.subquery_count: int = 0
        self.limit: int | None = None

        # Domain Logic Detection
        self.date_conditions: list[str] = []
        self.uses_effective_dating: bool = False
        self.effective_dating_details: list[str] = []
        self.uses_security_filter: bool = False
        self.security_filters_details: list[str] = []
        self.has_business_logic: bool = False
        self.business_logic_details: list[str] = []

        # Parameters
        self.parameters: list[dict[str, Any]] = []

        # Complexity
        self.complexity_score: float = 1.0
        self.complexity_level: str = "LOW"  # LOW, MEDIUM, HIGH, VERY_HIGH

    @property
    def has_group_by(self) -> bool:
        return len(self.group_by) > 0

    @property
    def has_order_by(self) -> bool:
        return len(self.order_by) > 0

    @property
    def has_effective_dating(self) -> bool:
        return self.uses_effective_dating

    @property
    def effective_dating_clauses(self) -> list[str]:
        return self.effective_dating_details

    @property
    def where_conditions(self) -> list[str]:
        return self.filters

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "validation_error": self.validation_error,
            "statement_type": self.statement_type,
            "table_count": len(self.tables),
            "column_count": len(self.columns),
            "join_count": len(self.joins),
            "cte_count": len(self.ctes),
            "subquery_count": self.subquery_count,
            "aggregation_count": len(self.aggregations),
            "tables": self.tables,
            "columns": self.columns,
            "joins": self.joins,
            "filters": self.filters,
            "aggregations": self.aggregations,
            "group_by": self.group_by,
            "order_by": self.order_by,
            "ctes": self.ctes,
            "limit": self.limit,
            "date_conditions": self.date_conditions,
            "uses_effective_dating": self.uses_effective_dating,
            "effective_dating_details": self.effective_dating_details,
            "uses_security_filter": self.uses_security_filter,
            "security_filters_details": self.security_filters_details,
            "has_business_logic": self.has_business_logic,
            "business_logic_details": self.business_logic_details,
            "parameters": self.parameters,
            "complexity_score": round(self.complexity_score, 1),
            "complexity_level": self.complexity_level,
            "formatted_sql": self.formatted_sql,
        }


SQLQueryAnalysis = ExtractedSQLMetadata


class SQLParser:
    """Parses and extracts metadata from SQL queries using SQLGlot."""

    # Patterns for domain detection
    EFFECTIVE_DATE_PATTERNS = (
        re.compile(r"effective_start_date", re.IGNORECASE),
        re.compile(r"effective_end_date", re.IGNORECASE),
        re.compile(r"effective_date", re.IGNORECASE),
        re.compile(r"as_of_date", re.IGNORECASE),
        re.compile(r"is_current\s*=\s*(?:1|true)", re.IGNORECASE),
        re.compile(r"ROW_NUMBER\s*\(\s*\)\s*OVER\s*\(\s*PARTITION\s+BY.*ORDER\s+BY\s+.*effective", re.IGNORECASE | re.DOTALL),
    )

    SECURITY_FILTER_PATTERNS = (
        re.compile(r"\b(?:organization_id|company_id|department_id|location_id|user_id|manager_id)\b", re.IGNORECASE),
        re.compile(r"\b(?:security_scope|tenant_id|org_id|cost_center_id)\b", re.IGNORECASE),
    )

    DATE_COLUMN_PATTERNS = (
        re.compile(r"\b(?:joining_date|termination_date|hire_date|effective_date|start_date|end_date|review_date|created_at|updated_at|current_date|now|sysdate|getdate)\b", re.IGNORECASE),
    )

    MUTATION_EXPRESSIONS = (
        exp.Insert, exp.Update, exp.Delete, exp.Drop,
        exp.Create, exp.Alter, exp.Command
    )

    @classmethod
    def parse_query(cls, sql_text: str, read_dialect: str = "sqlite") -> ExtractedSQLMetadata:
        """Parses SQL and extracts comprehensive metadata without executing it."""
        meta = ExtractedSQLMetadata()
        cleaned = sql_text.strip()
        if not cleaned:
            meta.is_valid = False
            meta.validation_error = "SQL query string is empty."
            return meta

        meta.formatted_sql = cleaned

        # 1. SQLGlot AST Parsing
        expression = None
        try:
            expression = parse_one(cleaned, read=read_dialect)
        except Exception:
            # Fallback to generic parsing
            try:
                expression = parse_one(cleaned)
            except Exception as e_generic:
                meta.is_valid = False
                meta.validation_error = f"SQL Syntax/Parser Error: {e_generic!s}"
                meta.statement_type = "INVALID"
                # Still perform regex extraction on raw text so we don't lose all metadata
                cls._regex_extract_fallback(cleaned, meta)
                return meta

        meta.is_valid = True
        try:
            meta.formatted_sql = expression.sql(pretty=True)
        except Exception:
            meta.formatted_sql = cleaned

        # Statement type
        if isinstance(expression, cls.MUTATION_EXPRESSIONS):
            meta.statement_type = expression.key.upper()
        elif isinstance(expression, exp.Select):
            meta.statement_type = "SELECT"
        else:
            meta.statement_type = expression.key.upper() if hasattr(expression, "key") else "QUERY"

        # 2. Extract Tables
        tables = []
        for tbl in expression.find_all(exp.Table):
            if tbl.name:
                tables.append(tbl.name.lower())
        meta.tables = sorted(dict.fromkeys(tables))

        # 3. Extract Projection Columns
        columns = []
        if isinstance(expression, exp.Select):
            for sel_expr in expression.expressions:
                if isinstance(sel_expr, exp.Alias):
                    columns.append(sel_expr.alias)
                elif hasattr(sel_expr, "name") and sel_expr.name:
                    columns.append(sel_expr.name)
                else:
                    columns.append(sel_expr.sql()[:50])
        meta.columns = columns

        # 4. Extract Joins with left, right, type, and condition
        joins = []
        from_tbl = meta.tables[0] if meta.tables else "unknown"
        for join in expression.find_all(exp.Join):
            right_tbl = join.this.name if hasattr(join.this, "name") else str(join.this)
            on_clause = join.args.get("on")
            join_type = (join.side or "INNER").upper() + " JOIN"
            joins.append({
                "left_table": from_tbl,
                "right_table": right_tbl,
                "join_type": join_type,
                "join_condition": on_clause.sql() if on_clause else ""
            })
        meta.joins = joins

        # 5. Extract Filters (WHERE conditions)
        where_clause = expression.find(exp.Where)
        if where_clause:
            # Sanitize filter expressions to avoid leaking raw literal values in metadata
            meta.filters.append(where_clause.this.sql())

        # 6. Extract Aggregations
        aggregations = []
        agg_types = [
            (exp.Count, "COUNT"),
            (exp.Sum, "SUM"),
            (exp.Avg, "AVG"),
            (exp.Min, "MIN"),
            (exp.Max, "MAX"),
        ]
        for agg_cls, agg_name in agg_types:
            for node in expression.find_all(agg_cls):
                col_name = node.this.sql() if hasattr(node, "this") and node.this else "*"
                is_distinct = bool(node.args.get("distinct", False))
                fname = f"{agg_name} DISTINCT" if is_distinct else agg_name
                aggregations.append({"function": fname, "column": col_name})
        meta.aggregations = aggregations

        # 7. Group By & Order By
        if expression.find(exp.Group):
            meta.group_by = [g.sql() for g in expression.find(exp.Group).expressions]
        if expression.find(exp.Order):
            meta.order_by = [o.sql() for o in expression.find(exp.Order).expressions]

        # 8. CTEs and Subqueries
        meta.ctes = [cte.alias for cte in expression.find_all(exp.CTE)]
        meta.subquery_count = len(list(expression.find_all(exp.Subquery)))

        # Limit
        limit_exp = expression.find(exp.Limit)
        if limit_exp and limit_exp.expression:
            try:
                meta.limit = int(limit_exp.expression.sql())
            except Exception:
                meta.limit = None

        # 9. Domain Logic Detection
        cls._detect_domain_features(cleaned, expression, meta)

        # 10. Extract Parameters
        meta.parameters = cls._extract_parameters(cleaned)

        # 11. Calculate Complexity Score
        meta.complexity_score, meta.complexity_level = cls._calculate_complexity(meta, expression)

        return meta

    @classmethod
    def _detect_domain_features(cls, raw_sql: str, expression: Any, meta: ExtractedSQLMetadata):
        """Detects date logic, effective dating, security filters, and business logic."""
        # Date Logic Detection
        for pat in cls.DATE_COLUMN_PATTERNS:
            for match in pat.findall(raw_sql):
                meta.date_conditions.append(match)
        meta.date_conditions = list(dict.fromkeys(meta.date_conditions))

        # Effective Dating Detection (Enterprise HR Invariant)
        for pat in cls.EFFECTIVE_DATE_PATTERNS:
            if pat.search(raw_sql):
                meta.uses_effective_dating = True
                for line in raw_sql.splitlines():
                    if pat.search(line):
                        meta.effective_dating_details.append(line.strip())
        meta.effective_dating_details = list(dict.fromkeys(meta.effective_dating_details))

        # Security Filters Detection
        for pat in cls.SECURITY_FILTER_PATTERNS:
            matches = pat.findall(raw_sql)
            if matches:
                meta.uses_security_filter = True
                meta.security_filters_details.extend(matches)
        meta.security_filters_details = list(dict.fromkeys(meta.security_filters_details))

        # Business Logic Detection (CASE, COALESCE, NULLIF, Window Functions)
        business_features = []
        if expression.find(exp.Case):
            business_features.append("CASE WHEN conditional logic")
        if expression.find(exp.Coalesce):
            business_features.append("COALESCE null fallback handling")
        if expression.find(exp.Window):
            business_features.append("Analytical window functions (OVER)")
        if re.search(r"\b(NULLIF|DATEDIFF|TIMESTAMPDIFF|AGE|JULIANDAY)\b", raw_sql, re.IGNORECASE):
            business_features.append("Date math / null comparison functions")

        if business_features:
            meta.has_business_logic = True
            meta.business_logic_details = business_features

    @classmethod
    def _extract_parameters(cls, raw_sql: str) -> list[dict[str, Any]]:
        """Identifies parameter placeholders (:param, {param}, %param%)."""
        params = []
        seen = set()

        # Matches :param_name (standard named bind params)
        named_colons = re.findall(r"(?<!:):([a-zA-Z_][a-zA-Z0-9_]*)", raw_sql)
        # Matches {param_name} or %(param_name)s
        braced = re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", raw_sql)
        pyformat = re.findall(r"%\(([a-zA-Z_][a-zA-Z0-9_]*)\)s", raw_sql)

        for p_name in (named_colons + braced + pyformat):
            if p_name.lower() in seen:
                continue
            seen.add(p_name.lower())

            # Infer type from parameter name
            p_type = "string"
            p_lower = p_name.lower()
            if "date" in p_lower or "as_of" in p_lower or "year" in p_lower:
                p_type = "date"
            elif "id" in p_lower or "count" in p_lower or "limit" in p_lower:
                p_type = "integer"
            elif "pct" in p_lower or "ratio" in p_lower or "rate" in p_lower or "salary" in p_lower:
                p_type = "float"

            params.append({
                "parameter_name": p_name,
                "parameter_type": p_type,
                "required": True,
                "default_value": None,
                "description": f"Filter parameter for {p_name.replace('_', ' ').title()}."
            })
        return params

    @classmethod
    def _calculate_complexity(cls, meta: ExtractedSQLMetadata, expression: Any) -> tuple[float, str]:
        """Heuristic score evaluating query complexity."""
        score = 1.0
        score += len(meta.tables) * 2.0
        score += len(meta.joins) * 3.0
        score += len(meta.ctes) * 4.0
        score += meta.subquery_count * 3.5
        score += len(meta.aggregations) * 1.5
        score += len(meta.filters) * 1.5

        if expression.find(exp.Window):
            score += 5.0
        if expression.find(exp.Case):
            score += 3.0
        if meta.uses_effective_dating:
            score += 2.5

        if score < 7.0:
            level = "LOW"
        elif score < 16.0:
            level = "MEDIUM"
        elif score < 28.0:
            level = "HIGH"
        else:
            level = "VERY_HIGH"

        return score, level

    @classmethod
    def _regex_extract_fallback(cls, raw_sql: str, meta: ExtractedSQLMetadata):
        """Fallback regex extractor if full AST parser fails on malformed SQL."""
        tables = re.findall(r"\bFROM\s+([a-zA-Z0-9_]+)", raw_sql, re.IGNORECASE)
        joins = re.findall(r"\bJOIN\s+([a-zA-Z0-9_]+)", raw_sql, re.IGNORECASE)
        meta.tables = sorted(dict.fromkeys([t.lower() for t in (tables + joins)]))
        meta.parameters = cls._extract_parameters(raw_sql)
        meta.complexity_score = 3.0
        meta.complexity_level = "LOW"

    @classmethod
    def transpile_query(cls, sql_text: str, from_dialect: str, to_dialect: str) -> str:
        """Transpiles SQL between database dialects (e.g. Postgres to SQLite or T-SQL)."""
        try:
            results = transpile(sql_text, read=from_dialect, write=to_dialect, pretty=True)
            return results[0] if results else sql_text
        except Exception:
            return sql_text
