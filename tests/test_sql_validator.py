"""Unit tests for SQL Parser and Security Validator."""

from backend.database.connection_manager import connection_manager
from sql.parser import SQLParser
from sql.validator import SQLValidator


def test_parser_extracts_ast():
    sql = """
    SELECT d.name, COUNT(e.id) AS cnt
    FROM departments d
    JOIN employees e ON d.id = e.department_id
    WHERE e.status = 'Active' AND e.is_current = 1
      AND e.effective_start_date <= CURRENT_DATE
    GROUP BY d.name
    ORDER BY cnt DESC
    LIMIT 50;
    """
    analysis = SQLParser.parse_query(sql)
    assert analysis.statement_type == "SELECT"
    assert "departments" in analysis.tables
    assert "employees" in analysis.tables
    assert analysis.has_effective_dating is True
    assert analysis.has_group_by is True
    assert analysis.has_order_by is True
    assert analysis.limit == 50


def test_validator_accepts_valid_read_only_query():
    schema = connection_manager.get_schema()
    sql = "SELECT first_name, last_name, email FROM employees WHERE status = 'Active';"
    is_valid, msg, _analysis = SQLValidator.validate(sql, discovered_schema=schema)
    assert is_valid is True
    assert "successfully validated" in msg


def test_validator_blocks_mutations():
    schema = connection_manager.get_schema()
    dangerous_queries = [
        "DROP TABLE employees;",
        "DELETE FROM departments WHERE id = 1;",
        "UPDATE employees SET status = 'Terminated';",
        "ALTER TABLE employees ADD COLUMN ssn VARCHAR(11);",
        "TRUNCATE TABLE performance_reviews;"
    ]
    for q in dangerous_queries:
        is_valid, msg, _ = SQLValidator.validate(q, discovered_schema=schema)
        assert is_valid is False
        assert "Security Violation" in msg or "forbidden" in msg or "Only read-only" in msg


def test_validator_blocks_sql_injection_chaining():
    schema = connection_manager.get_schema()
    chained_query = "SELECT * FROM departments; DROP TABLE employees"
    is_valid, msg, _ = SQLValidator.validate(chained_query, discovered_schema=schema)
    assert is_valid is False
    assert "Multi-statement" in msg


def test_validator_blocks_unauthorized_table():
    schema = connection_manager.get_schema()
    bad_table_sql = "SELECT * FROM secret_financial_ledgers"
    is_valid, msg, _ = SQLValidator.validate(bad_table_sql, discovered_schema=schema)
    assert is_valid is False
    assert "unauthorized" in msg.lower()
