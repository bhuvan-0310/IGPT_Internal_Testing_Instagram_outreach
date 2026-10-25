import streamlit as st
from sqlalchemy import select, func
from src.database import get_session
from src.models import Prospect, Campaign
from src.ui import page_header, require_database

st.set_page_config(page_title="Instagram Outreach Studio", page_icon="✉️", layout="wide")
require_database()

st.title("Instagram Outreach Studio")
st.caption("Local-first workspace for prospect data, campaign preparation, and human-reviewed outreach.")
st.info("Prospects, campaigns, AI-assisted drafting, voice assets, the asset library, outreach tracking, and the supervised browser workspace are all active. Set OPENAI_API_KEY in .env to enable AI drafting and voice generation.")

with get_session() as session:
    prospect_count = session.scalar(select(func.count()).select_from(Prospect)) or 0
    campaign_count = session.scalar(select(func.count()).select_from(Campaign)) or 0
    new_count = session.scalar(select(func.count()).select_from(Prospect).where(Prospect.status == "New")) or 0

c1, c2, c3 = st.columns(3)
c1.metric("Prospects", prospect_count)
c2.metric("Campaigns", campaign_count)
c3.metric("New prospects", new_count)

st.subheader("Getting started")
st.markdown("""
1. Open **Prospects** and import an Apify export or CSV/Excel file.
2. Review the mapped fields and any duplicate records.
3. Create a campaign under **Campaigns**.
4. Continue with the Message Studio after configuring your OpenAI API key.
""")
st.subheader("Safety by design")
st.markdown("""
- Instagram credentials are entered directly into the dedicated browser, not stored by this app.
- Messages remain drafts until reviewed and approved.
- No stealth, bot-detection evasion, or unattended bulk unsolicited follow requests/DMs.
- Use imported data only where collection and contact are permitted.
""")
