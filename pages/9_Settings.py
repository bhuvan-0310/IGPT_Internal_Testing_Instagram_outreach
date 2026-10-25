import streamlit as st
from src.config import (
    ASSET_DIRECTORY, AUDIO_DIRECTORY, BROWSER_PROFILE_DIR, MAX_UPLOAD_SIZE_MB,
    OPENAI_API_KEY, OPENAI_TEXT_MODEL, OPENAI_AUDIO_MODEL, masked_database_url,
)
from src.database import check_connection
from src.ui import page_header

st.set_page_config(page_title="Settings | Outreach Studio", layout="wide")
page_header("Settings", "Configuration overview and diagnostics. Secrets are loaded from environment variables — never paste API keys or Instagram passwords into this page.")

st.subheader("Database")
ok, message = check_connection()
if ok:
    st.success(message)
else:
    st.error(message)
st.caption(f"Configured URL: {masked_database_url()}")
if st.button("Re-check connection"):
    st.rerun()

st.subheader("OpenAI")
if OPENAI_API_KEY:
    st.success(f"API key configured. Text model: `{OPENAI_TEXT_MODEL}` · Audio model: `{OPENAI_AUDIO_MODEL}`")
else:
    st.warning("OPENAI_API_KEY is not set. Message Studio and Voice Studio generation will show an actionable error until it's added to .env.")

st.subheader("Playwright browser workspace")
try:
    import playwright  # noqa: F401
    st.success(f"Playwright is installed. Dedicated profile directory: `{BROWSER_PROFILE_DIR}`")
except ImportError:
    st.warning("Playwright is not installed. Run 'pip install playwright && playwright install chromium' to enable the Browser Workspace.")

st.subheader("Storage")
c1, c2 = st.columns(2)
c1.write(f"Asset directory: `{ASSET_DIRECTORY}`")
c1.write(f"Audio directory: `{AUDIO_DIRECTORY}`")
c2.write(f"Max upload size: {MAX_UPLOAD_SIZE_MB} MB")

st.subheader("Data retention and deletion")
st.markdown("""
- Prospects, campaigns, drafts, outreach events, and follow-ups live in PostgreSQL until you delete them.
- Deleting an asset or voice asset in the app also removes its file from disk immediately.
- This app never auto-deletes data. Use `pg_dump`/`psql` for backup and restore (see README).
- The dedicated browser profile under `data/browser_profile/` holds your Instagram session cookies for that profile only — delete the folder to sign out everywhere.
""")

st.subheader("Safety")
st.markdown("""
- Instagram credentials are entered directly into the dedicated browser window, never into this app.
- Approving a message draft means it is cleared for manual use — it does not send anything.
- Recording outreach in the tracker or browser workspace only logs what you already did manually.
- Prospects marked **Do Not Contact** cannot have new outreach recorded or follow-ups scheduled (enforced in the service layer, not just the UI).
""")
