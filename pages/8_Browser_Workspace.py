import streamlit as st
from src.ui import page_header

st.set_page_config(page_title="Browser Workspace | Outreach Studio", layout="wide")
page_header("Browser Workspace", "Phase 4 — scaffold")
st.warning("Browser automation is not enabled yet. The planned workflow launches a dedicated persistent profile and leaves Instagram authentication directly to you.")
st.markdown("""
- Open a prospect profile or source Reel.
- Review prospect context and an approved draft.
- Copy the draft and perform permitted actions yourself.
- Confirm the result before it is logged.
""")
st.button("Launch dedicated browser", disabled=True)
