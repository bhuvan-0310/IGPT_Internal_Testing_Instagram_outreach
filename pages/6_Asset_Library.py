import streamlit as st
from src.ui import page_header

st.set_page_config(page_title="Asset Library | Outreach Studio", layout="wide")
page_header("Asset Library", "Phase 3 — scaffold")
st.info("Planned: safely managed PDFs, catalogue links, product facts, images and audio files.")
st.file_uploader("Upload an asset", type=["pdf", "png", "jpg", "jpeg", "mp3", "wav"], disabled=True)
