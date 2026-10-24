import streamlit as st
from src.ui import page_header

st.set_page_config(page_title="Message Studio | Outreach Studio", layout="wide")
page_header("Message Studio", "Phase 2 — scaffold")
st.warning("The UI placeholder is ready; connect the OpenAI drafting service in Phase 2. Drafts will require human review before use.")
st.text_area("Message draft", placeholder="Generated and editable draft will appear here…")
st.button("Generate draft", disabled=True)
st.caption("Planned: prospect + campaign context, multiple variants, grounded personalization, revision history, approval and export.")
