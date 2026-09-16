"""Phase 17: Complete Documentation & Final Demonstration Workflow Tests."""

import os
import subprocess
import sys


def test_all_14_documentation_files_exist_and_comprehensive():
    """Verify presence and substance of all 14 required enterprise documentation guides."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    required_docs = [
        "README.md",
        "docs/architecture.md",
        "docs/module_reference.md",
        "docs/installation_guide.md",
        "docs/configuration_guide.md",
        "docs/database_setup_guide.md",
        "docs/api_documentation.md",
        "docs/user_manual.md",
        "docs/admin_manual.md",
        "docs/security_documentation.md",
        "docs/testing_documentation.md",
        "docs/ai_evaluation_report.md",
        "docs/deployment_guide.md",
        "docs/troubleshooting_guide.md",
        "docs/existing_sql_knowledge_reuse.md"
    ]

    for doc_path in required_docs:
        full_path = os.path.join(project_root, doc_path)
        assert os.path.exists(full_path), f"Missing required documentation: {doc_path}"
        
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        
        # Verify document is substantive (> 250 characters)
        assert len(content) > 250, f"Document '{doc_path}' is too brief ({len(content)} characters)"


def test_canonical_demonstration_script_execution():
    """Verify execution of the 12-stage canonical demonstration script."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script_path = os.path.join(project_root, "scripts", "demo_canonical_workflow.py")
    assert os.path.exists(script_path)

    # Run demonstration script
    res = subprocess.run(
        [sys.executable, script_path],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=60,
        check=False
    )

    assert res.returncode == 0, f"Demonstration failed with stderr: {res.stderr}"
    stdout = res.stdout

    # Verify all 12 stages are announced in output
    for stage_num in range(1, 13):
        assert f"[Stage {stage_num}/12]" in stdout, f"Missing Stage {stage_num} in demonstration output"

    assert "DEMONSTRATION COMPLETED SUCCESSFULLY" in stdout
    assert "Show monthly employee attrition by department for 2026." in stdout
    assert "Export [CSV]" in stdout
    assert "Export [EXCEL]" in stdout
    assert "Export [PDF]" in stdout
