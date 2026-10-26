import pandas as pd
import streamlit as st
from sqlalchemy import select
from src.database import get_session
from src.models import CAMPAIGN_ACTION_LABELS, DEFAULT_CAMPAIGN_ACTIONS, Campaign, MessageDraft, Prospect
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
    campaigns = session.scalars(select(Campaign).order_by(Campaign.name)).all()

if not campaigns:
    st.info("Create a campaign first.")
    st.stop()

campaign_options = {c.name: c.id for c in campaigns}
campaign_label = st.selectbox("Campaign", list(campaign_options.keys()))
campaign_id = campaign_options[campaign_label]


def contact_methods_for(actions: list[str]) -> list[str]:
    methods = []
    if "follow_request" in actions:
        methods.append("Instagram follow request")
    if "message" in actions:
        methods.append("Instagram DM")
    if "pdf" in actions:
        methods.append("Instagram DM with PDF/catalogue")
    if "voice" in actions:
        methods.append("Instagram DM with voice message")
    return methods


def next_pending_prospect(current_id: int, pending_ids: list[int]) -> int | None:
    if not pending_ids:
        return None
    if current_id not in pending_ids:
        return pending_ids[0]
    current_index = pending_ids.index(current_id)
    return pending_ids[(current_index + 1) % len(pending_ids)]


with get_session() as session:
    campaign = session.get(Campaign, campaign_id)
    campaign_actions = campaign.campaign_actions or DEFAULT_CAMPAIGN_ACTIONS
    action_contact_methods = contact_methods_for(campaign_actions)
    prospects = session.scalars(
        select(Prospect)
        .where(Prospect.campaign_id == campaign_id, Prospect.status != "Do Not Contact")
        .order_by(Prospect.username)
    ).all()
    completed_ids = outreach_service.completed_prospect_ids(
        session, campaign_id, action_contact_methods
    )
    completed_ids &= {prospect.id for prospect in prospects}

if not prospects:
    st.info("No contactable prospects are assigned to this campaign yet. Assign prospects in the Prospects page first.")
    st.stop()

runner_started_key = f"campaign_runner_started_{campaign_id}"
st.subheader("1. Sign in and review the campaign")
with st.container(border=True):
    st.caption("Your Instagram login happens directly in the dedicated browser window. This app never asks for or stores your password.")
    if st.button("Open dedicated browser for Instagram sign-in", icon=":material/login:"):
        try:
            browser_module.open_url("https://www.instagram.com/")
            st.success("The dedicated browser is open. Sign in there, then return here to review and start the campaign.")
        except browser_module.BrowserLaunchError as e:
            st.error(str(e))

    st.markdown("**Configured actions**")
    for action in campaign_actions:
        st.write(f":material/check_circle: {CAMPAIGN_ACTION_LABELS.get(action, action)}")
    st.caption(f"{len(prospects)} contactable prospect(s) are assigned to this campaign.")

    signed_in = st.checkbox(
        "I am signed in to the intended Instagram account in the dedicated browser.",
        key=f"campaign_runner_signed_in_{campaign_id}",
    )
    reviewed = st.checkbox(
        "I have reviewed the campaign actions and prospect list.",
        key=f"campaign_runner_reviewed_{campaign_id}",
    )
    if st.button(
        "Start manual campaign runner",
        type="primary",
        icon=":material/play_arrow:",
        disabled=not (signed_in and reviewed),
    ):
        with get_session() as session:
            session.get(Campaign, campaign_id).status = "Active"
        st.session_state[runner_started_key] = True
        st.rerun()

if not st.session_state.get(runner_started_key, False):
    st.info("Complete the sign-in and review confirmations above, then start the manual campaign runner.")
    st.stop()

pending_ids = [prospect.id for prospect in prospects if prospect.id not in completed_ids]
metric_total, metric_done, metric_remaining = st.columns(3)
metric_total.metric("Prospects", len(prospects), border=True)
metric_done.metric("Completed", len(completed_ids), border=True)
metric_remaining.metric("Remaining", len(pending_ids), border=True)

st.subheader(f"Prospect queue ({len(prospects)})")
queue = pd.DataFrame([
    {
        "Username": f"@{prospect.username}",
        "Status": prospect.status,
        "Campaign progress": "Completed" if prospect.id in completed_ids else "Ready",
        "Display name": prospect.display_name or "",
        "Profile": browser_module.profile_url_for(prospect.username, prospect.profile_url),
    }
    for prospect in prospects
])
st.dataframe(
    queue,
    column_config={"Profile": st.column_config.LinkColumn("Profile")},
    hide_index=True,
    alt="Prospects assigned to the selected campaign",
)

all_prospect_ids = [prospect.id for prospect in prospects]
cycle_key = f"campaign_runner_cycle_{campaign_id}"
preferred_key = f"campaign_runner_preferred_{campaign_id}"
cycle = st.session_state.get(cycle_key, 0)
preferred_id = st.session_state.get(preferred_key)
default_id = preferred_id if preferred_id in all_prospect_ids else (pending_ids[0] if pending_ids else all_prospect_ids[0])
prospect_id = st.selectbox(
    "Current prospect",
    all_prospect_ids,
    index=all_prospect_ids.index(default_id),
    format_func=lambda prospect_id: next(
        f"@{prospect.username} ({'completed' if prospect.id in completed_ids else prospect.status})"
        for prospect in prospects if prospect.id == prospect_id
    ),
    key=f"campaign_runner_prospect_{campaign_id}_{cycle}",
)
if st.button("Next prospect (leave current unrecorded)", disabled=len(pending_ids) < 2):
    st.session_state[preferred_key] = next_pending_prospect(prospect_id, pending_ids)
    st.session_state[cycle_key] = cycle + 1
    st.rerun()

with get_session() as session:
    prospect = session.get(Prospect, prospect_id)
    campaign = session.get(Campaign, campaign_id)
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
    cc2.link_button(
        "View Instagram profile",
        browser_module.profile_url_for(prospect.username, prospect.profile_url),
    )

    st.subheader("Campaign action plan")
    for action in campaign_actions:
        st.write(f":material/check_circle: {CAMPAIGN_ACTION_LABELS.get(action, action)}")

    chosen_draft_id = None
    if "message" in campaign_actions:
        st.subheader("Approved draft")
        if not approved_drafts:
            st.info("No approved draft for this prospect/campaign yet. Approve one in Message Studio, or proceed without one.")
        else:
            labels = [f"Variant {d.variant_label} (v{d.version})" for d in approved_drafts]
            choice = st.selectbox("Choose the approved variant to use", labels)
            chosen = approved_drafts[labels.index(choice)]
            chosen_draft_id = chosen.id
            st.text_area("Draft content (copy this manually into Instagram)", value=chosen.content, height=120, disabled=True)

    resource_actions = {"pdf", "voice"} & set(campaign_actions)
    if resource_actions:
        st.caption("Prepare the selected PDF/catalogue or voice asset in its studio first, then attach or share it manually in Instagram.")

st.divider()
st.subheader("Open the dedicated browser")
url_to_open = browser_module.profile_url_for(prospect.username, prospect.profile_url)
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
    contact_method = st.selectbox("What did you do?", action_contact_methods + ["Other"])
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
            if contact_method in action_contact_methods:
                st.session_state[preferred_key] = next_pending_prospect(prospect_id, pending_ids)
                st.session_state[cycle_key] = cycle + 1
            st.success("Recorded. This reflects what you already did manually.")
            st.rerun()
        except outreach_service.DoNotContactError as e:
            st.error(str(e))
