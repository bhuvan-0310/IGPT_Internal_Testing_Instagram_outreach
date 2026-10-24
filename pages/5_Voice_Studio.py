import streamlit as st
from src.ui import page_header

st.set_page_config(page_title="Voice Studio | Outreach Studio", layout="wide")
page_header("Voice Studio", "Phase 3 — scaffold")
st.info("Planned: voice script generation, supported text-to-speech integration, audio preview and upload.")
st.file_uploader("Upload an existing audio recording", type=["mp3", "wav", "m4a"], disabled=True)
