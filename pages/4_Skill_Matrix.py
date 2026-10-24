import streamlit as st
from src.ui import page_header

st.set_page_config(page_title="Skill Matrix | Outreach Studio", layout="wide")
page_header("Skill Matrix", "Phase 2 — scaffold")
st.info("The editable rule editor and saved skill profiles will be implemented in Phase 2.")
st.dataframe([
    {"Skill": "Personalization", "Enabled": True, "Priority": 1},
    {"Skill": "Tone", "Enabled": True, "Priority": 2},
    {"Skill": "Product factuality", "Enabled": True, "Priority": 1},
    {"Skill": "Repetition control", "Enabled": True, "Priority": 3},
    {"Skill": "Compliance", "Enabled": True, "Priority": 1},
], use_container_width=True, hide_index=True)
