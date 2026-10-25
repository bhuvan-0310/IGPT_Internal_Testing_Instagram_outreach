import streamlit as st
from sqlalchemy import select
from src.database import get_session
from src.models import Campaign, MessageDraft, Prospect
from src.integrations import browser as browser_module
from src.services import outreach as outreach_service
from src.ui import page_header, require_database

st.set_page_config(page_title="Browser Workspace | Outreach Studio", layout="wide")
require_database()
page_header("Browser Workspace", "A dedicated, persistent browser profile for manually completing outreach. You authenticate to Instagram yourself, directly in the window — this app never sees or stores your password.")

st.warning(
    "This workspace does not automate Instagram actions, bypass CAPTCHAs, or send anything on its own. "
    "It opens a profile page for you, shows the approved draft, and then lets you confirm — after you've "
    "done it yourself — that the action was completed."
)

with get_session() as session:
    prospects = session.scalars(select(Prospect).where(Prospect.status != "Do Not Contact").order_by(Prospect.username)).all()
    campaigns = session.scalars(select(Campaign).order_by(Campaign.name)).all()

if not prospects or not campaigns:
    st.info("Need at least one contactable prospect and one campaign.")
    st.stop()

prospect_options = {f"@{p.username} ({p.status})": p.id for p in prospects}
campaign_options = {c.name: c.id for c in campaigns}

c1, c2 = st.columns(2)
prospect_label = c1.selectbox("Prospect", list(prospect_options.keys()))
campaign_label = c2.selectbox("Campaign", list(campaign_options.keys()))
prospect_id = prospect_options[prospect_label]
campaign_id = campaign_options[campaign_label]

with get_session() as session:
    prospect = session.get(Prospect, prospect_id)
    approved_drafts = session.scalars(
        select(MessageDraft).where(
            MessageDraft.prospect_id == prospect_id, MessageDraft.campaign_id == campaign_id,
            MessageDraft.status == "Approved",
        )
    ).all()

    st.subheader("Prospect context")
    cc1, cc2 = st.columns(2)
    cc1.markdown(f"**@{prospect.username}**  \n{prospect.display_name or ''}")
    cc1.caption(prospect.bio or "No bio on file.")
    cc2.write(f"Status: {prospect.status}")
    cc2.write(f"Profile: {prospect.profile_url or '—'}")

    st.subheader("Approved draft")
    if not approved_drafts:
        st.info("No approved draft for this prospect/campaign yet. Approve one in Message Studio, or proceed without one.")
        chosen_draft_id = None
    else:
        labels = [f"Variant {d.variant_label} (v{d.version})" for d in approved_drafts]
        choice = st.selectbox("Choose the approved variant to use", labels)
        chosen = approved_drafts[labels.index(choice)]
        chosen_draft_id = chosen.id
        st.text_area("Draft content (copy this manually into Instagram)", value=chosen.content, height=120, disabled=True)

st.divider()
st.subheader("Open the dedicated browser")
url_to_open = prospect.profile_url or f"https://www.instagram.com/{prospect.username}/"
st.caption(f"Will open: {url_to_open}")

bc1, bc2 = st.columns(2)
if bc1.button("Launch dedicated browser and open profile", type="primary"):
    if not browser_module.is_safe_instagram_or_source_url(url_to_open):
        st.error("This URL does not look safe to open (must be http:// or https://).")
    else:
        try:
            browser_module.open_url(url_to_open)
            st.success("Opened in the dedicated browser window. Sign in there yourself if needed, then perform the action manually.")
        except browser_module.BrowserLaunchError as e:
            st.error(str(e))
if bc2.button("Close dedicated browser"):
    browser_module.close_dedicated_browser()
    st.success("Closed.")

st.divider()
st.subheader("Confirm what you did")
st.caption("Only record this after you've manually completed the action in the browser above.")
with st.form("confirm_outreach"):
    contact_method = st.selectbox("What did you do?", ["Instagram DM", "Instagram comment reply", "Other"])
    response_status = st.selectbox("Result so far", ["No response", "Replied", "Positive", "Negative", "Converted"])
    outcome = st.text_input("Outcome (optional)")
    notes = st.text_area("Notes (optional)")
    if st.form_submit_button("Record completed outreach", type="primary"):
        try:
            with get_session() as session:
                prospect = session.get(Prospect, prospect_id)
                outreach_service.record_event(
                    session, prospect, campaign_id, contact_method=contact_method,
                    response_status=response_status, outcome=outcome.strip() or None,
                    notes=notes.strip() or None, draft_id=chosen_draft_id,
                )
            st.success("Recorded. This reflects what you already did manually.")
            st.rerun()
        except outreach_service.DoNotContactError as e:
            st.error(str(e))
