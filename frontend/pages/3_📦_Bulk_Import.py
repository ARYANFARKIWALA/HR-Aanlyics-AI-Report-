"""Module 2: Bulk SQL File Import Interface.

Workflow:
Upload Multiple SQL Files -> Parse -> Validate -> Detect Duplicates -> Preview -> Confirm & Ingest -> Import Summary
"""

import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.dirname(CURRENT_DIR)
PROJECT_ROOT = os.path.dirname(FRONTEND_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd
import streamlit as st

from backend.database.connection import SessionLocal
from backend.database.connection_manager import connection_manager
from backend.database.models import User
from backend.services.sql_repository_service import SQLRepositoryService

st.set_page_config(page_title="Bulk SQL Import", page_icon="📦", layout="wide")

if "current_username" not in st.session_state:
    st.session_state.current_username = "admin"

db_session = SessionLocal()
current_user = db_session.query(User).filter(User.username == st.session_state.current_username).first()
if not current_user:
    current_user = db_session.query(User).first()

if current_user.role not in ["admin", "hr_manager"]:
    st.error("⛔ Unauthorized: Only ADMIN and HR_ADMIN roles can bulk import SQL reports.")
    st.stop()

st.markdown("## 📦 Bulk SQL Reports Importer")
st.markdown("*Ingest dozens or hundreds of existing enterprise .sql files at once into the SQL Knowledge Repository.*")
st.divider()

# Select Target Database (from Module 1)
dbs = connection_manager.list_databases_safe()
db_options = [d["database_id"] for d in dbs]
selected_db_id = st.selectbox("Select Target HR Database (Module 1):", db_options, index=0)

# Multi-file uploader
uploaded_files = st.file_uploader(
    "Upload multiple .sql or .txt report files:",
    type=["sql", "txt"],
    accept_multiple_files=True
)

if uploaded_files:
    st.info(f"📁 **{len(uploaded_files)}** files selected for ingestion.")

    # In-memory dictionary
    files_dict = {}
    for f in uploaded_files:
        b = f.read()
        files_dict[f.name] = b.decode("utf-8", errors="replace")

    col_b1, col_b2 = st.columns([2, 5])
    with col_b1:
        start_import_btn = st.button("🚀 Process & Ingest All Files", type="primary", width='stretch')

    if start_import_btn:
        with st.spinner("Parsing, validating, and checking duplicates across files..."):
            summary = SQLRepositoryService.bulk_import(
                session=db_session,
                files_dict=files_dict,
                database_id=selected_db_id,
                user=current_user
            )

            st.success("🎉 Bulk Import Completed!")

            # Metric Cards
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Files Processed", summary["total_files"])
            m2.metric("Valid Reports Imported", summary["imported_valid"])
            m3.metric("Duplicates Detected", summary["duplicates_detected"])
            m4.metric("Invalid Syntax Queries", summary["invalid_queries"])

            st.divider()

            # Detailed Ingestion Grid
            st.markdown("#### Detailed File Ingestion Summary:")
            df_details = pd.DataFrame(summary["details"])
            st.dataframe(df_details, width='stretch')

            # Download summary JSON / CSV
            csv_data = df_details.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Download Import Summary Log (CSV)",
                data=csv_data,
                file_name="sql_bulk_import_summary.csv",
                mime="text/csv"
            )

db_session.close()
