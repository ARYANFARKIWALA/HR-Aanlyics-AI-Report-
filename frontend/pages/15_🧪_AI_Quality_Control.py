"""Module 13: Streamlit AI Quality Control, Evaluation Benchmark & Penetration Testing Dashboard.

Provides:
- Executive Scorecard (SQL Validity %, Execution Accuracy %, Security Defense %, RAG Hit Rate %, Latency)
- Interactive Golden Dataset Benchmark Runner
- Detailed Test Case Matrix & SQL Inspection
- Adversarial Penetration Stress Testing & Injection Gate Verification
"""

import os
import sys
import datetime
import streamlit as st
import pandas as pd

# Ensure project root is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.database.connection import SessionLocal, init_db
from evaluation.schemas import EvaluationRunRequest
from evaluation.evaluator import EvaluationEngine
from evaluation.adversarial_runner import AdversarialSecurityRunner

st.set_page_config(
    page_title="AI Quality Control - HR Analytics AI",
    page_icon="🧪",
    layout="wide"
)

init_db()
db = SessionLocal()

st.title("🧪 AI Quality Control & Evaluation Dashboard")
st.caption("Module 13 — Enterprise AI Testing, Golden Benchmarks, SQL Accuracy, RAG Grounding & Adversarial Defense")

st.markdown("---")

tab_benchmark, tab_matrix, tab_adversarial, tab_dataset = st.tabs([
    "📊 Evaluation Scorecard",
    "📋 Detailed Test Matrix",
    "🛡️ Adversarial Stress Tests",
    "📚 Golden Dataset Catalog"
])

# =========================================================================
# TAB 1: EVALUATION SCORECARD
# =========================================================================
with tab_benchmark:
    st.subheader("System Quality Benchmarking")
    st.write("Run the automated golden test suite to evaluate Text-to-SQL validity, RAG grounding, security enforcement, and execution accuracy.")

    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([2, 2, 2])
    with col_ctrl1:
        cat_select = st.selectbox("Benchmark Category:", ["All Categories", "Headcount", "Attrition", "Compensation", "Diversity", "Performance", "Adversarial"])
    with col_ctrl2:
        inc_adv = st.checkbox("Include Adversarial Tests", value=True)
    with col_ctrl3:
        run_bench_btn = st.button("🚀 Run Quality Benchmark", type="primary")

    if run_bench_btn or "last_eval_summary" not in st.session_state:
        cat_param = None if cat_select == "All Categories" else cat_select
        with st.spinner("Executing golden benchmark suite across AST validator, RAG, and execution engine..."):
            req = EvaluationRunRequest(category=cat_param, include_adversarial=inc_adv)
            summary = EvaluationEngine.run_benchmark(db=db, req=req)
            st.session_state["last_eval_summary"] = summary

    summary = st.session_state.get("last_eval_summary")
    if summary:
        st.markdown(f"**Last Run Timestamp:** `{summary.timestamp}` | Total Evaluated Cases: **{summary.total_cases}**")

        # KPI Scorecard
        kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)
        with kpi_col1:
            st.metric("SQL Validity Rate", f"{summary.sql_validity_rate}%", delta="AST Parsed")
        with kpi_col2:
            st.metric("Execution Accuracy", f"{summary.execution_accuracy_rate}%", delta="Verified Rows")
        with kpi_col3:
            st.metric("Security Defense Rate", f"{summary.security_defense_rate}%", delta="Zero-Trust Gate")
        with kpi_col4:
            st.metric("RAG Hit Rate", f"{summary.rag_hit_rate}%", delta="Rule Grounded")
        with kpi_col5:
            st.metric("Avg Latency", f"{summary.avg_latency_ms:.1f} ms", delta="End-to-End")

        st.markdown("---")
        # Pass/Fail Bar
        pass_pct = (summary.passed_cases / summary.total_cases * 100.0) if summary.total_cases > 0 else 0
        st.write(f"**Overall Benchmark Pass Rate:** **{summary.passed_cases}/{summary.total_cases}** ({pass_pct:.1f}%)")
        st.progress(min(1.0, max(0.0, pass_pct / 100.0)))

# =========================================================================
# TAB 2: DETAILED TEST MATRIX
# =========================================================================
with tab_matrix:
    st.subheader("Test Case Execution Matrix")
    if not summary or not summary.results:
        st.info("Run the benchmark in the Scorecard tab to populate results.")
    else:
        table_rows = []
        for r in summary.results:
            is_pass = r.security_passed if r.is_adversarial else (r.sql_valid and r.security_passed and r.execution_success)
            table_rows.append({
                "Test ID": r.test_id,
                "Category": r.category,
                "Question": r.question,
                "Type": "Adversarial" if r.is_adversarial else "Standard",
                "Gate Status": r.validation_status,
                "SQL Valid": "✅" if r.sql_valid else "❌",
                "Sec Gated": "✅" if r.security_passed else "❌",
                "Exec": "✅" if r.execution_success else "❌",
                "Verdict": "🟢 PASS" if is_pass else "🔴 FAIL",
                "Latency (ms)": f"{r.latency_ms:.1f}"
            })
        st.dataframe(pd.DataFrame(table_rows), width='stretch')

        st.markdown("#### Test Case Inspector")
        sel_tc = st.selectbox(
            "Select Test Case to inspect details:",
            options=[r.test_id for r in summary.results],
            format_func=lambda tid: f"{tid} - {next((r.question for r in summary.results if r.test_id == tid), '')}"
        )
        target_res = next((r for r in summary.results if r.test_id == sel_tc), None)
        if target_res:
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.markdown(f"**Question:** {target_res.question}")
                st.markdown(f"**Category:** `{target_res.category}` | **Type:** `{'Adversarial' if target_res.is_adversarial else 'Standard'}`")
                st.markdown(f"**Validation Status:** `{target_res.validation_status}`")
                if target_res.error_message:
                    st.warning(f"**Reported Message / Violation:** {target_res.error_message}")
            with col_d2:
                st.markdown("**Evaluated SQL Query:**")
                st.code(target_res.generated_sql or "-- No SQL generated", language="sql")

# =========================================================================
# TAB 3: ADVERSARIAL STRESS TESTS
# =========================================================================
with tab_adversarial:
    st.subheader("🛡️ Adversarial Penetration & Prompt Injection Defense")
    st.write("Stress tests the Module 7 Zero-Trust Validator Gate against mutation injection, comment evasion, destructive drops, and unauthorized schema exfiltration.")

    if st.button("⚡ Run Adversarial Penetration Suite", type="primary"):
        with st.spinner("Executing attack payloads against security gate..."):
            adv_results = AdversarialSecurityRunner.run_penetration_tests(db)
            st.session_state["adv_results"] = adv_results

    adv_res = st.session_state.get("adv_results")
    if not adv_res:
        # Run on load by default
        adv_res = AdversarialSecurityRunner.run_penetration_tests(db)
        st.session_state["adv_results"] = adv_res

    if adv_res:
        blocked_count = sum(1 for a in adv_res if a.blocked)
        total_attacks = len(adv_res)
        defense_rate = (blocked_count / total_attacks * 100.0) if total_attacks > 0 else 100.0

        adv_k1, adv_k2, adv_k3 = st.columns(3)
        with adv_k1:
            st.metric("Total Attack Vectors", total_attacks)
        with adv_k2:
            st.metric("Attacks Neutralized", f"{blocked_count}/{total_attacks}")
        with adv_k3:
            st.metric("Defense Block Rate", f"{defense_rate:.1f}%", delta="Zero Compromises")

        st.markdown("##### Attack Vector Neutralization Log")
        adv_table = []
        for a in adv_res:
            adv_table.append({
                "Attack Vector": a.attack_type,
                "Payload Snippet": a.payload[:45] + "..." if len(a.payload) > 45 else a.payload,
                "Gate Verdict": "🛡️ BLOCKED" if a.blocked else "⚠️ LEAKED",
                "Defending Engine": a.blocked_by,
                "Policy Enforcement": a.details
            })
        st.dataframe(pd.DataFrame(adv_table), width='stretch')

# =========================================================================
# TAB 4: GOLDEN DATASET CATALOG
# =========================================================================
with tab_dataset:
    st.subheader("Curated Golden Benchmark Questions")
    st.write("The golden test set defines approved expected schemas, columns, keywords, and security boundaries across all core HR analytics domains.")

    golden_data = EvaluationEngine.load_golden_dataset()
    if golden_data:
        g_rows = []
        for g in golden_data:
            g_rows.append({
                "ID": g["id"],
                "Category": g["category"],
                "Question": g["question"],
                "Expected Tables": ", ".join(g.get("expected_tables", [])),
                "Keywords": ", ".join(g.get("expected_sql_keywords", [])),
                "Expected Gate": g.get("expected_status", "APPROVED"),
                "Adversarial": "Yes" if g.get("is_adversarial", False) else "No"
            })
        st.dataframe(pd.DataFrame(g_rows), width='stretch')

db.close()
