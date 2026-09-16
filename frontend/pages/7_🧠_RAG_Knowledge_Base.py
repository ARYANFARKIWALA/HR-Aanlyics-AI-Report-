"""Module 5: Streamlit RAG Knowledge Base Governance & Search Sandbox.

Provides:
- Knowledge Base Status & KPIs (Documents, Semantic Chunks, Vector Embeddings)
- Source Distribution Breakdown (M1/M3 Schemas, M2 SQL Reports, M4 Active Business Rules)
- Full Ingestion & Incremental Re-index Trigger
- Interactive Hybrid Semantic Search Sandbox
- Explainability & "Why Retrieved?" Inspector
- Prompt Injection-Safe <ORGANIZATIONAL_KNOWLEDGE> Preview
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
from rag.rag_service import RAGService

st.set_page_config(
    page_title="RAG Knowledge Base - HR Analytics AI",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 RAG Knowledge Base & Context Engine")
st.caption("Module 5 — Dense Vector Embeddings, Hybrid Retrieval, Prioritized Injection-Safe Context")

init_db()
db = SessionLocal()
service = RAGService(db)

# Database Selector & Sync Controls
registered_dbs = connection_manager.list_databases_safe()
db_options = [d["database_id"] for d in registered_dbs] if registered_dbs else ["sqlite_hr_default"]

col_db, col_act1, col_act2 = st.columns([3, 2, 2])
with col_db:
    selected_db_id = st.selectbox("Target HR Database Knowledge Scope", db_options, index=0)

with col_act1:
    st.write("")
    st.write("")
    if st.button("🔄 Sync & Re-index Knowledge Base", width='stretch'):
        with st.spinner(f"Ingesting approved knowledge for '{selected_db_id}'..."):
            res = service.ingest_database(database_id=selected_db_id)
            st.success(f"Indexed {res.get('documents_indexed', 0)} documents and {res.get('chunks_indexed', 0)} chunks!")

with col_act2:
    st.write("")
    st.write("")
    if st.button("⚠️ Clear & Rebuild Index", width='stretch'):
        with st.spinner(f"Rebuilding knowledge index for '{selected_db_id}'..."):
            res = service.rebuild(database_id=selected_db_id)
            st.warning(f"Rebuilt index: {res.get('chunks_indexed', 0)} chunks indexed.")

# 1. Knowledge Base KPIs
stats = service.get_stats(database_id=selected_db_id)

st.markdown("---")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Indexed Documents", stats.get("total_documents", 0))
kpi2.metric("Semantic Chunks", stats.get("total_chunks", 0))
kpi3.metric("Dense Embeddings", stats.get("total_embeddings", 0))
kpi4.metric("Security Level Invariant", "Zero Raw PII")

# 2. Source Breakdown & Chunk Types
tab_search, tab_breakdown, tab_context_preview = st.tabs([
    "🔍 Interactive Retrieval Sandbox",
    "📊 Knowledge Source Breakdown",
    "🛡️ Injection-Safe Context Preview"
])

with tab_breakdown:
    col_src, col_chk = st.columns(2)
    with col_src:
        st.subheader("Indexed Documents by Source")
        by_source = stats.get("by_source_type", {})
        if by_source:
            df_src = pd.DataFrame([{"Source Type": k, "Count": v} for k, v in by_source.items()])
            st.dataframe(df_src, width='stretch')
        else:
            st.info("No documents indexed yet. Click 'Sync & Re-index Knowledge Base' above.")

    with col_chk:
        st.subheader("Semantic Chunks by Type")
        by_chk = stats.get("by_chunk_type", {})
        if by_chk:
            df_chk = pd.DataFrame([{"Chunk Type": k, "Count": v} for k, v in by_chk.items()])
            st.dataframe(df_chk, width='stretch')
        else:
            st.info("No chunks generated yet.")

with tab_search:
    st.subheader("Test Hybrid Knowledge Retrieval")
    st.caption("Tests dense vector similarity + keyword token matching + security priority boosting.")

    col_q, col_top = st.columns([5, 1])
    with col_q:
        search_query = st.text_input(
            "Natural Language Query / Reporting Question",
            value="Show active employees attrition rate with salary by department"
        )
    with col_top:
        top_k = st.slider("Top K", min_value=1, max_value=15, value=6)

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        inc_schema = st.checkbox("Include Schemas (M1/M3)", value=True)
    with col_f2:
        inc_rules = st.checkbox("Include Business Rules (M4)", value=True)
    with col_f3:
        inc_reports = st.checkbox("Include SQL Reports (M2)", value=True)

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        run_hybrid = st.button("🚀 Fast Hybrid Search", type="primary", width='stretch')
    with col_btn2:
        run_phase5 = st.button("🎯 Full Knowledge Retrieval Pipeline", width='stretch')

    if run_phase5:
        with st.spinner("Executing Phase 5 Knowledge Retrieval Pipeline..."):
            pipeline_res = service.retrieve_knowledge(
                query=search_query,
                database_id=selected_db_id,
                top_k=top_k
            )

        # 1. Query Understanding
        st.markdown("#### 🧭 1. Query Understanding & Entity Extraction")
        und = pipeline_res.get("query_understanding", {})
        u1, u2, u3, u4 = st.columns(4)
        u1.metric("Identified Entities", ", ".join(und.get("entities", [])) or "None")
        u2.metric("Target Metrics", ", ".join(und.get("metrics", [])) or "None")
        u3.metric("Temporal Scope", und.get("temporal_scope", "ALL"))
        u4.metric("Candidate Tables", ", ".join(und.get("candidate_tables", [])) or "None")

        # 2. Knowledge Retrieval Categorization
        st.markdown(f"#### 📦 2. Retrieved Knowledge Assets ({pipeline_res.get('total_items_retrieved', 0)} total)")

        p_tab1, p_tab2, p_tab3, p_tab4 = st.tabs([
            f"📚 Relevant SQL ({len(pipeline_res.get('relevant_sql', []))})",
            f"🗄️ Database Schema ({len(pipeline_res.get('schema_tables', []))})",
            f"⚖️ Business Rules ({len(pipeline_res.get('business_rules', []))})",
            f"📖 Glossary & Defs ({len(pipeline_res.get('glossary_definitions', []))})"
        ])

        with p_tab1:
            for sql_item in pipeline_res.get("relevant_sql", []):
                st.markdown(f"**[{int(sql_item.get('score', 0)*100)}% Match] {sql_item.get('title')}** `Source: {sql_item.get('source_type')}`")
                st.code(sql_item.get("text", ""), language="markdown")

        with p_tab2:
            for sch_item in pipeline_res.get("schema_tables", []):
                st.markdown(f"**[{int(sch_item.get('score', 0)*100)}% Match] {sch_item.get('title')}** `Source: {sch_item.get('source_type')}`")
                st.code(sch_item.get("text", ""), language="markdown")

        with p_tab3:
            for rule_item in pipeline_res.get("business_rules", []):
                st.markdown(f"**[{int(rule_item.get('score', 0)*100)}% Match] {rule_item.get('title')}** `Source: {rule_item.get('source_type')}`")
                st.code(rule_item.get("text", ""), language="markdown")

        with p_tab4:
            for gloss_item in pipeline_res.get("glossary_definitions", []):
                st.markdown(f"**[{int(gloss_item.get('score', 0)*100)}% Match] {gloss_item.get('title')}** `Source: {gloss_item.get('source_type')}`")
                st.code(gloss_item.get("text", ""), language="markdown")

        # 3. Context Package
        with st.expander("🛡️ View Prioritized Context Delivered to AI", expanded=False):
            st.text_area("Prioritized Context Envelope", pipeline_res.get("context_package", ""), height=250)

    elif run_hybrid:
        with st.spinner("Executing hybrid retrieval..."):
            hits = service.search(
                query=search_query,
                database_id=selected_db_id,
                top_k=top_k,
                include_schema=inc_schema,
                include_rules=inc_rules,
                include_reports=inc_reports
            )

        if not hits:
            st.warning("No relevant knowledge retrieved. Knowledge base may be empty or score threshold not met.")
        else:
            st.success(f"Retrieved {len(hits)} matching knowledge chunks:")
            for i, hit in enumerate(hits, 1):
                sec_badge = "🛡️ CRITICAL" if hit.get("security_level") == "CRITICAL" else "📄 STANDARD"
                score_pct = int(hit.get("score", 0) * 100)

                with st.expander(f"#{i} [{score_pct}% Match] [{hit.get('source_type')}] {hit.get('title')} ({sec_badge})", expanded=(i == 1)):
                    st.markdown(f"**Chunk Type:** `{hit.get('chunk_type')}` | **Tables:** `{', '.join(hit.get('table_names', [])) or 'None'}`")
                    st.code(hit.get("text", ""), language="markdown")

                    # Why retrieved transparency
                    why = hit.get("why_retrieved", {})
                    if why:
                        st.markdown("**Why Retrieved? (Explainability Breakdown):**")
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Semantic Similarity", f"{int(why.get('semantic_similarity', 0)*100)}%")
                        c2.metric("Keyword Overlap", f"{int(why.get('keyword_match_ratio', 0)*100)}%")
                        c3.metric("Matched Tables", ", ".join(why.get("matched_tables", [])) or "None")


with tab_context_preview:
    st.subheader("Delimited Text-to-SQL Prompt Context")
    st.caption("Shows the exact prioritized context delivered to Module 6 inside `<ORGANIZATIONAL_KNOWLEDGE>` tags.")

    ctx_query = st.text_input("Context Test Query", value="Active headcount and turnover for engineering department")
    if st.button("Generate Structured Context", key="btn_ctx"):
        ctx_response = service.get_context_for_query(
            query=ctx_query,
            database_id=selected_db_id,
            top_k=6
        )

        if ctx_response.status == "INSUFFICIENT_CONTEXT":
            st.warning(f"⚠️ Status: {ctx_response.status} — {ctx_response.message}")
        else:
            st.success(f"Status: {ctx_response.status}")
            if ctx_response.conflicts_detected:
                st.error(f"Rule Conflicts Detected: {len(ctx_response.conflicts_detected)}")
                for cf in ctx_response.conflicts_detected:
                    st.write(cf)

            col_t, col_c = st.columns(2)
            col_t.markdown(f"**Identified Tables:** `{', '.join(ctx_response.relevant_tables)}`")
            col_c.markdown(f"**Identified Columns:** `{', '.join(ctx_response.relevant_columns)}`")

            st.text_area("Prompt Injection-Delimited Context for LLM", ctx_response.context, height=350)
