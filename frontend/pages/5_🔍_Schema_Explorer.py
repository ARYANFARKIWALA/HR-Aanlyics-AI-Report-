"""Module 3: Streamlit Schema Explorer & Metadata Intelligence Dashboard.

Provides an enterprise interactive interface for:
- Schema Health Dashboard (Completeness, Verification %, Sensitive Fields)
- Table & Column Browser with HR Semantic Classifications
- Entity-Relationship & Join Visualizer (Database FKs, SQL Usage, Manual)
- Human Business Metadata Editor & Verification Workflow
- Schema Drift & Change History Log
- LlamaIndex-ready RAG Knowledge Preview
"""

import os
import sys

# Ensure project root is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PAGES_DIR = CURRENT_DIR
FRONTEND_DIR = os.path.dirname(PAGES_DIR)
PROJECT_ROOT = os.path.dirname(FRONTEND_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
import pandas as pd
from backend.database.connection import SessionLocal, init_db
from backend.database.connection_manager import connection_manager
from backend.database.models_schema import SchemaTable, SchemaRelationship
from schema.service import SchemaIntelligenceService
from rag.schema_knowledge_builder import SchemaKnowledgeBuilder

st.set_page_config(
    page_title="Schema & Metadata Explorer - HR Analytics AI",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 HR Database Schema & Metadata Intelligence")
st.caption("Module 3 — Deep Schema Discovery, HR Semantic Taxonomy, SQL Usage Mining & Human Governance")

# Initialize DB session
init_db()
db = SessionLocal()
service = SchemaIntelligenceService(db)

# -------------------------------------------------------------
# Top Bar: Database Selector & Discovery Controls
# -------------------------------------------------------------
registered_dbs = connection_manager.list_databases_safe()
db_options = [d["database_id"] for d in registered_dbs] if registered_dbs else ["sqlite_hr_default"]

col_db, col_btn1, col_btn2 = st.columns([3, 1.2, 1.2])

with col_db:
    selected_db_id = st.selectbox("Target HR Database Connection", db_options, index=0)

with col_btn1:
    st.write("")
    st.write("")
    if st.button("🚀 Discover Schema", width='stretch', type="primary"):
        with st.spinner("Introspecting database structure and mining SQL usage..."):
            try:
                res = service.discover_schema(database_id=selected_db_id)
                st.success(f"Discovered {res['tables_discovered']} tables, {res['columns_discovered']} columns, {res['relationships_discovered']} joins!")
                st.rerun()
            except Exception as e:
                st.error(f"Discovery error: {e}")

with col_btn2:
    st.write("")
    st.write("")
    if st.button("🔄 Refresh Schema", width='stretch'):
        with st.spinner("Re-inspecting and detecting schema drift..."):
            try:
                res = service.refresh_schema(database_id=selected_db_id)
                changes_count = res.get("changes_detected_count", 0)
                if changes_count > 0:
                    st.warning(f"Schema refreshed! Detected {changes_count} schema change(s).")
                else:
                    st.info("Schema refreshed. No structural drift detected.")
                st.rerun()
            except Exception as e:
                st.error(f"Refresh error: {e}")

st.divider()

# -------------------------------------------------------------
# KPI Cards: Schema Health Dashboard
# -------------------------------------------------------------
health = service.get_schema_health(database_id=selected_db_id)

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
with kpi1:
    score = health["health_score"]
    status_label = health["readiness_status"]
    st.metric("Health Score", f"{score}%", help="Weighted completeness of descriptions, relationships, and verification.")
    st.caption(f"AI Readiness: **{status_label}**")

with kpi2:
    tbl_cnt = health["table_count"]
    vw_cnt = health["views_count"]
    st.metric("Tables / Views", f"{tbl_cnt} / {vw_cnt}")
    st.caption(f"{health['described_tables_pct']}% Described")

with kpi3:
    col_cnt = health["column_count"]
    st.metric("Columns Total", col_cnt)
    st.caption(f"{health['described_columns_pct']}% Defined")

with kpi4:
    rel_cnt = health["relationship_count"]
    st.metric("Join Paths", rel_cnt)
    st.caption("FK + Inferred + Manual")

with kpi5:
    sens_cnt = health["sensitive_fields_count"]
    ver_pct = health["verified_columns_pct"]
    st.metric("Sensitive Fields", sens_cnt)
    st.caption(f"{ver_pct}% Verified Columns")

st.progress(score / 100.0)

st.divider()

# If no tables discovered yet, prompt user
if health["table_count"] == 0:
    st.warning("No schema metadata discovered for this database connection yet. Click **🚀 Discover Schema** above to introspect tables, columns, and relationships.")
    db.close()
    st.stop()

# -------------------------------------------------------------
# Main Content Tabs
# -------------------------------------------------------------
tab_tables, tab_rels, tab_usage, tab_drift, tab_rag = st.tabs([
    "🗂️ Tables & Columns Explorer",
    "🔗 Entity Relationships & Joins",
    "📊 SQL Usage Intelligence",
    "🕒 Schema Drift & Change Log",
    "🧠 RAG Knowledge Preview"
])

# -------------------------------------------------------------
# TAB 1: Tables & Columns Explorer
# -------------------------------------------------------------
with tab_tables:
    col_f1, col_f2, col_f3 = st.columns([2, 2, 3])
    with col_f1:
        entity_options = ["ALL", "EMPLOYEE", "DEPARTMENT", "JOB_POSITION", "COMPENSATION", "PAYROLL", "PERFORMANCE", "LEAVE_ATTENDANCE", "BENEFITS", "OTHER"]
        sel_entity = st.selectbox("Filter Entity Type", entity_options, index=0)
    with col_f2:
        status_options = ["ALL", "AUTO_DISCOVERED", "PENDING_REVIEW", "VERIFIED"]
        sel_status = st.selectbox("Filter Status", status_options, index=0)
    with col_f3:
        search_kw = st.text_input("Search tables or attributes...", placeholder="e.g. employee, salary, hire_date")

    tables_list = service.get_tables(
        database_id=selected_db_id,
        entity_type=sel_entity if sel_entity != "ALL" else None,
        status=sel_status if sel_status != "ALL" else None,
        search=search_kw if search_kw else None
    )

    st.write(f"Showing **{len(tables_list)}** tables/views matching filters:")

    if not tables_list:
        st.info("No tables match the selected criteria.")
    else:
        # Table Selection
        table_names = [t["table_name"] for t in tables_list]
        selected_tbl_name = st.selectbox("Select Table to Inspect & Edit:", table_names, index=0)

        # Fetch Table Detail
        selected_tbl_meta = next(t for t in tables_list if t["table_name"] == selected_tbl_name)
        tbl_detail = service.get_table_detail(selected_tbl_meta["id"])

        if tbl_detail:
            # Header Info
            c_h1, c_h2, c_h3, c_h4 = st.columns(4)
            with c_h1:
                st.write(f"**Technical Name:** `{tbl_detail['table_name']}`")
                st.write(f"**Business Entity:** `{tbl_detail['business_entity']}`")
            with c_h2:
                st.write(f"**Type:** `{tbl_detail['table_type']}`")
                st.write(f"**Approx. Rows:** `{tbl_detail['row_count_approx']:,}`")
            with c_h3:
                imp_color = "red" if tbl_detail['importance_level'] == "CRITICAL" else ("orange" if tbl_detail['importance_level'] == "HIGH" else "blue")
                st.markdown(f"**Importance:** :{imp_color}[**{tbl_detail['importance_level']}**] ({tbl_detail['importance_score']}/100)")
                st.write(f"**Effective Dating:** {'✅ Yes' if tbl_detail['uses_effective_dating'] else '❌ No'}")
            with c_h4:
                status_badge = "🟢 VERIFIED" if tbl_detail["status"] == "VERIFIED" else "🟡 AUTO_DISCOVERED"
                st.write(f"**Status:** {status_badge}")
                if tbl_detail["status"] != "VERIFIED":
                    if st.button("✅ Mark Table & Columns Verified", key=f"v_tbl_{tbl_detail['id']}"):
                        service.verify_table(tbl_detail["id"])
                        st.success("Table and columns marked as VERIFIED!")
                        st.rerun()

            # Table Metadata Edit Expander
            with st.expander("✏️ Edit Table Business Metadata"):
                with st.form(f"edit_tbl_form_{tbl_detail['id']}"):
                    new_bname = st.text_input("Business Name", value=tbl_detail.get("business_name") or "")
                    new_desc = st.text_area("Description", value=tbl_detail.get("description") or "")
                    new_entity = st.selectbox(
                        "Business Entity",
                        ["EMPLOYEE", "DEPARTMENT", "JOB_POSITION", "COMPENSATION", "PAYROLL", "PERFORMANCE", "LEAVE_ATTENDANCE", "BENEFITS", "RECRUITMENT", "LOCATION", "ORGANIZATION_UNIT", "OTHER"],
                        index=["EMPLOYEE", "DEPARTMENT", "JOB_POSITION", "COMPENSATION", "PAYROLL", "PERFORMANCE", "LEAVE_ATTENDANCE", "BENEFITS", "RECRUITMENT", "LOCATION", "ORGANIZATION_UNIT", "OTHER"].index(tbl_detail.get("business_entity") or "OTHER")
                    )
                    submitted = st.form_submit_button("Save Table Metadata")
                    if submitted:
                        service.update_table_metadata(tbl_detail["id"], {
                            "business_name": new_bname,
                            "description": new_desc,
                            "business_entity": new_entity
                        })
                        st.success("Table metadata updated!")
                        st.rerun()

            # Columns Grid
            st.markdown("#### 📋 Columns Dictionary & Semantic Attributes")
            cols_data = tbl_detail.get("columns", [])

            df_cols = pd.DataFrame([
                {
                    "ID": c["id"],
                    "Column Name": c["column_name"],
                    "Business Name": c["business_name"],
                    "Data Type": c["data_type"],
                    "Normalized": c["normalized_data_type"],
                    "Role": "PK" if c["is_primary_key"] else ("FK" if c["is_foreign_key"] else ("Metric" if c["is_metric"] else "Dimension")),
                    "Date Role": c["date_role"] if c["date_role"] != "NONE" else "-",
                    "Sensitive": f"🔒 {c['sensitive_category']}" if c["is_sensitive"] else "No",
                    "Status": c["status"],
                    "Definition": c["business_definition"]
                }
                for c in cols_data
            ])

            st.dataframe(df_cols, width='stretch', hide_index=True)

            # Column Detail & Editor
            with st.expander("🛠️ Inspect & Edit Specific Column"):
                col_choices = {f"{c['column_name']} ({c['business_name']})": c for c in cols_data}
                sel_col_label = st.selectbox("Choose Column to Edit", list(col_choices.keys()))
                sel_col = col_choices[sel_col_label]

                with st.form(f"col_edit_form_{sel_col['id']}"):
                    c_ed1, c_ed2 = st.columns(2)
                    with c_ed1:
                        c_bname = st.text_input("Column Business Name", value=sel_col.get("business_name") or "")
                        c_concept = st.text_input("HR Concept Taxonomy", value=sel_col.get("hr_concept") or "")
                        c_def = st.text_area("Business Definition", value=sel_col.get("business_definition") or "")
                    with c_ed2:
                        c_sens = st.checkbox("Is Sensitive Field (PII / Financial)", value=bool(sel_col.get("is_sensitive")))
                        c_sens_cat = st.selectbox(
                            "Sensitivity Category",
                            ["NONE", "FINANCIAL", "PERSONAL_IDENTIFIER", "HEALTH", "RESTRICTED", "PUBLIC_INTERNAL"],
                            index=["NONE", "FINANCIAL", "PERSONAL_IDENTIFIER", "HEALTH", "RESTRICTED", "PUBLIC_INTERNAL"].index(sel_col.get("sensitive_category") or "NONE")
                        )
                        c_metric = st.checkbox("Is Numeric Metric", value=bool(sel_col.get("is_metric")))
                        c_agg = st.selectbox(
                            "Default Aggregation",
                            ["NONE", "SUM", "AVG", "COUNT", "MIN", "MAX"],
                            index=["NONE", "SUM", "AVG", "COUNT", "MIN", "MAX"].index(sel_col.get("default_aggregation") or "NONE")
                        )
                        c_dim = st.checkbox("Is Grouping Dimension", value=bool(sel_col.get("is_dimension")))

                    c_save = st.form_submit_button("Save Column Attributes")
                    if c_save:
                        service.update_column_metadata(sel_col["id"], {
                            "business_name": c_bname,
                            "hr_concept": c_concept,
                            "business_definition": c_def,
                            "is_sensitive": c_sens,
                            "sensitive_category": c_sens_cat,
                            "is_metric": c_metric,
                            "default_aggregation": c_agg,
                            "is_dimension": c_dim,
                            "status": "VERIFIED"
                        })
                        st.success("Column updated and marked as VERIFIED!")
                        st.rerun()

# -------------------------------------------------------------
# TAB 2: Entity Relationships & Joins
# -------------------------------------------------------------
with tab_rels:
    st.markdown("### 🔗 Discovered & Inferred Table Relationships")
    st.caption("Includes database foreign key constraints, SQL usage patterns inferred from Module 2, and manual join definitions.")

    col_rf1, col_rf2 = st.columns([2, 4])
    with col_rf1:
        rel_src_filter = st.selectbox("Filter by Source", ["ALL", "DATABASE_FOREIGN_KEY", "SQL_USAGE", "MANUAL"])

    rels_list = service.get_relationships(
        database_id=selected_db_id,
        source=rel_src_filter if rel_src_filter != "ALL" else None
    )

    if rels_list:
        df_rels = pd.DataFrame([
            {
                "ID": r["id"],
                "Source Table": r["source_table"],
                "Source Column": r["source_column"],
                "Target Table": r["target_table"],
                "Target Column": r["target_column"],
                "Type": r["relationship_type"],
                "Source": r["relationship_source"],
                "Confidence": r["confidence"],
                "Usage Count": r["usage_count"],
                "Verified": "✅ Yes" if r["is_verified"] else "No",
                "Join Condition": r["join_condition"]
            }
            for r in rels_list
        ])
        st.dataframe(df_rels, width='stretch', hide_index=True)
    else:
        st.info("No relationships found for the selected filter.")

    # Add Manual Relationship Form
    st.markdown("#### ➕ Define Custom Manual Relationship")
    with st.expander("Add New Manual Join Link"):
        all_tables = [t["table_name"] for t in service.get_tables(database_id=selected_db_id)]
        with st.form("manual_rel_form"):
            r_c1, r_c2, r_c3 = st.columns(3)
            with r_c1:
                src_t = st.selectbox("Source Table", all_tables, key="mr_src_t")
                src_c = st.text_input("Source Column Name", placeholder="e.g. manager_id", key="mr_src_c")
            with r_c2:
                tgt_t = st.selectbox("Target Table", all_tables, key="mr_tgt_t")
                tgt_c = st.text_input("Target Column Name", placeholder="e.g. id", key="mr_tgt_c")
            with r_c3:
                cardinality = st.selectbox("Relationship Type", ["MANY_TO_ONE", "ONE_TO_MANY", "ONE_TO_ONE", "MANY_TO_MANY"])
                st.write("")
                st.write("")
                add_rel_btn = st.form_submit_button("Add Relationship")

            if add_rel_btn:
                if not src_c or not tgt_c:
                    st.error("Please enter both source and target column names.")
                else:
                    try:
                        service.add_manual_relationship(
                            database_id=selected_db_id,
                            data={
                                "source_table": src_t,
                                "source_column": src_c.strip(),
                                "target_table": tgt_t,
                                "target_column": tgt_c.strip(),
                                "relationship_type": cardinality
                            }
                        )
                        st.success("Manual relationship added successfully!")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Failed to add relationship: {ex}")

# -------------------------------------------------------------
# TAB 3: SQL Usage Intelligence
# -------------------------------------------------------------
with tab_usage:
    st.markdown("### 📊 Module 2 Historical SQL Usage Intelligence")
    st.caption("Mined from approved historical reports in Module 2's SQL repository to power table importance and join recommendations.")

    usage_metrics = service.get_usage_metrics(database_id=selected_db_id)

    u_col1, u_col2 = st.columns(2)
    with u_col1:
        st.markdown("#### Top Queried Tables")
        top_tables = usage_metrics.get("top_tables", [])
        if top_tables:
            df_top_t = pd.DataFrame(top_tables)
            st.dataframe(df_top_t, width='stretch', hide_index=True)
        else:
            st.info("No table usage recorded yet. Add reports in Module 2 to populate usage frequencies.")

    with u_col2:
        st.markdown("#### Top Queried Columns")
        top_cols = usage_metrics.get("top_columns", [])
        if top_cols:
            df_top_c = pd.DataFrame(top_cols)
            st.dataframe(df_top_c, width='stretch', hide_index=True)
        else:
            st.info("No column usage recorded yet.")

    st.markdown("#### Recurring Joins in SQL Catalog")
    top_joins = usage_metrics.get("top_joins", [])
    if top_joins:
        df_top_j = pd.DataFrame(top_joins)
        st.dataframe(df_top_j, width='stretch', hide_index=True)
    else:
        st.info("No recurring joins recorded yet.")

# -------------------------------------------------------------
# TAB 4: Schema Drift & Change Log
# -------------------------------------------------------------
with tab_drift:
    st.markdown("### 🕒 Schema Drift & Modification Audit Log")
    st.caption("Tracks additions, removals, and modifications of tables, columns, and data types across schema snapshots.")

    d_col1, d_col2 = st.columns([1, 2])
    with d_col1:
        st.markdown("#### Historical Snapshots")
        snapshots = service.get_snapshots(database_id=selected_db_id)
        if snapshots:
            df_snaps = pd.DataFrame(snapshots)
            st.dataframe(df_snaps, width='stretch', hide_index=True)
        else:
            st.info("No snapshots recorded.")

    with d_col2:
        st.markdown("#### Detected Changes")
        changes = service.get_schema_changes(database_id=selected_db_id, limit=50)
        if changes:
            df_changes = pd.DataFrame(changes)
            st.dataframe(df_changes, width='stretch', hide_index=True)
        else:
            st.info("No schema drift detected. The current schema matches the baseline snapshot.")

# -------------------------------------------------------------
# TAB 5: RAG Knowledge Preview
# -------------------------------------------------------------
with tab_rag:
    st.markdown("### 🧠 LlamaIndex RAG Knowledge Document Generation")
    st.caption("Structured text documents built from the enriched schema, ready for vector indexing and LLM prompt grounding in Module 5.")

    r_c1, r_c2 = st.columns([2, 1])
    with r_c1:
        tbl_preview = st.selectbox("Select Table Document to Preview", [t["table_name"] for t in tables_list], key="rag_preview_tbl")
    with r_c2:
        st.write("")
        st.write("")
        redact_check = st.checkbox("Simulate Non-Privileged Role (Redact Sensitive Fields)")

    chosen_tbl = service.db.query(SchemaTable).filter_by(database_id=selected_db_id, table_name=tbl_preview).first()
    
    if chosen_tbl:
        all_rels = service.db.query(SchemaRelationship).filter_by(database_id=selected_db_id).all()
        doc = SchemaKnowledgeBuilder.build_table_document(
            table=chosen_tbl,
            relationships=all_rels,
            redact_sensitive=redact_check
        )
        st.markdown("#### Document Metadata")
        st.json(doc.metadata)
        st.markdown("#### Document Content")
        st.code(doc.text_content, language="markdown")

db.close()
