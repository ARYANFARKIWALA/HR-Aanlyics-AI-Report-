"""Reusable Streamlit sidebar navigation and persona component."""

import streamlit as st
from sqlalchemy.orm import Session

from backend.database.models import User


def render_sidebar(db: Session) -> User:
    """Renders user persona selector and global navigation indicators."""
    with st.sidebar:
        st.markdown("### 🔐 Security & Identity")
        users = db.query(User).filter(User.is_active == True).all()
        user_map = {u.username: u for u in users}

        if "current_user_name" not in st.session_state:
            st.session_state["current_user_name"] = "admin"

        current_username = st.session_state["current_user_name"]
        default_index = list(user_map.keys()).index(current_username) if current_username in user_map else 0

        selected_user = st.selectbox(
            "Active User Persona:",
            options=list(user_map.keys()),
            index=default_index,
            key="global_persona_selector"
        )
        st.session_state["current_user_name"] = selected_user
        active_user = user_map.get(selected_user)

        if active_user:
            st.info(f"**Name:** {active_user.full_name}\n**Role:** `{active_user.role}`")

        st.markdown("---")
        st.markdown("### 🧭 Architecture")
        st.caption("Modules 1–14 fully operational.\nBackend: FastAPI on :8000\nUI: Streamlit on :8501")

        return active_user
