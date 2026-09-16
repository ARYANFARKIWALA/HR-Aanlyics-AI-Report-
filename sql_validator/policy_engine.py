"""Configurable Security Policies for SQL Validation."""

from .schemas import ValidationPolicy

# Default enterprise zero-trust policy
DEFAULT_POLICY = ValidationPolicy(
    allow_select_star=False,
    max_joins=5,
    disallow_cartesian=True,
    disallow_comments=True,
    require_where_on_large_tables=True,
    large_table_threshold_rows=1000,
    max_risk_score_auto_approval=65.0,
    token_ttl_minutes=15
)

# Standard list of tables considered large or requiring guarded WHERE clauses
LARGE_TABLES = {"employees", "compensation_history", "performance_reviews", "leave_records"}

# Safe SQL functions allowlist
SAFE_FUNCTIONS = {
    "count", "sum", "avg", "min", "max",
    "coalesce", "round", "upper", "lower", "trim",
    "length", "substr", "substring", "replace",
    "date", "strftime", "cast", "extract", "datediff",
    "case", "when", "then", "else", "end",
    "distinct", "concat", "ifnull", "nullif", "abs", "ceil", "floor"
}

# Dangerous / blocked functions and commands
FORBIDDEN_FUNCTIONS = {
    "xp_cmdshell", "benchmark", "sleep", "pg_sleep",
    "load_file", "into_outfile", "sysdate", "system_user",
    "session_user", "current_user", "schema", "database",
    "version", "user", "eval", "exec", "execute", "load_extension"
}
