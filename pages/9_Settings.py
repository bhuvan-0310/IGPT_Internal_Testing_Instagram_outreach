import streamlit as st
from src.config import DATABASE_URL, OPENAI_TEXT_MODEL, BROWSER_PROFILE_DIR
from src.ui import page_header

st.set_page_config(page_title="Settings | Outreach Studio", layout="wide")
page_header("Settings", "Configuration overview")
st.write("Database URL configured:", bool(DATABASE_URL))
st.write("OpenAI text model:", OPENAI_TEXT_MODEL)
st.write("Dedicated browser profile directory:", str(BROWSER_PROFILE_DIR))
st.caption("Secrets are loaded from environment variables. Do not paste API keys or Instagram passwords into this page.")
