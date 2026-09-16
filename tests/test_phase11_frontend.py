"""Comprehensive Tests for Phase 11 — Complete Streamlit Frontend."""

import ast
import pytest
import os


def test_frontend_app_syntax_and_structure():
    """Verify that frontend/app.py parses as valid Python and defines all required navigation sections."""
    app_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "app.py")
    with open(app_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Must be valid Python AST
    tree = ast.parse(content)
    assert tree is not None

    # Verify all 10 required navigation options are present
    required_navs = [
        "Dashboard",
        "Ask AI",
        "Reports",
        "SQL Repository",
        "Schema Explorer",
        "Business Rules",
        "Knowledge/RAG",
        "Query History",
        "Administration",
        "Settings"
    ]
    for nav in required_navs:
        assert f'"{nav}"' in content or f"'{nav}'" in content, f"Missing navigation option: {nav}"

    # Verify Main page branding and AI question prompt
    assert "HR ANALYTICS AI REPORT BUILDER" in content
    assert "Ask your HR question..." in content
    assert "Show employee count by department for 2026." in content
    assert "Generate Report" in content

    # Verify vertical 7-stage display flow sections
    assert "Question" in content
    assert "Relevant Knowledge" in content
    assert "Generated SQL" in content
    assert "Validation Status" in content
    assert "Results" in content
    assert "Charts" in content
    assert "Download Report" in content
    assert "Download CSV" in content
    assert "Download Excel" in content
    assert "Download PDF" in content
