import streamlit as st
from src.database import init_db


def page_header(title: str, subtitle: str = ""):
    st.title(title)
    if subtitle:
        st.caption(subtitle)


def require_database():
    """Verify DB connectivity at the top of a page; show an actionable error
    and stop rendering instead of crashing with a raw traceback."""
    try:
        init_db()
    except RuntimeError as exc:
        st.error(str(exc))
        st.stop()
