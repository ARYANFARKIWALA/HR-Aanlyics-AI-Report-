"""Reusable Streamlit header component."""


import streamlit as st

from config.settings import settings


def render_header(title: str, subtitle: str | None = None) -> None:
    """Renders a standardized enterprise header banner."""
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title(title)
        if subtitle:
            st.caption(subtitle)
    with col2:
        env_badge = settings.environment.upper()
        badge_color = "green" if env_badge == "PRODUCTION" else "orange"
        st.markdown(f"**Env:** `:{badge_color}[{env_badge}]`")
        st.markdown(f"**Version:** `{settings.app_version}`")
    st.markdown("---")
