from datetime import date, datetime, time, timezone
import pandas as pd
import streamlit as st
from sqlalchemy import select, or_
from src.database import get_session
from src.models import OUTREACH_STATUSES, Campaign, FollowUpTask, OutreachEvent, Prospect
from src.services import outreach as outreach_service
from src.services import followups as followups_service
from src.ui import page_header, require_database

st.set_page_config(page_title="Outreach Tracker | Outreach Studio", layout="wide")
require_database()
page_header("Outreach Tracker", "Search, filter, and record outreach activity. Recording an event means you already completed it manually — this page never sends anything.")

tab_search, tab_record, tab_followups = st.tabs(["Search & history", "Record outreach", "Follow-ups"])

with tab_search:
    with get_session() as session:
        campaigns = session.scalars(select(Campaign).order_by(Campaign.name)).all()
        campaign_filter_options = {"All campaigns": None}
        campaign_filter_options.update({c.name: c.id for c in campaigns})

        c1, c2, c3 = st.columns([2, 1, 1])
        query = c1.text_input("Search username or display name")
        status_filter = c2.multiselect("Status", OUTREACH_STATUSES, default=[])
        campaign_label = c3.selectbox("Campaign", list(campaign_filter_options.keys()))

        stmt = select(Prospect).order_by(Prospect.updated_at.desc())
        if query:
            like = f"%{query}%"
            stmt = stmt.where(or_(Prospect.username.ilike(like), Prospect.display_name.ilike(like)))
        if status_filter:
            stmt = stmt.where(Prospect.status.in_(status_filter))
        if campaign_filter_options[campaign_label]:
            stmt = stmt.where(Prospect.campaign_id == campaign_filter_options[campaign_label])
        prospects = session.scalars(stmt.limit(500)).all()

        if not prospects:
            st.info("No matching prospects.")
        for p in prospects:
            with st.expander(f"@{p.username} · {p.status}" + (f" · {p.campaign.name}" if p.campaign else "")):
                history = outreach_service.history_for(session, p.id)
                if not history:
                    st.caption("No outreach recorded yet.")
                else:
                    rows = [{
                        "Date": e.contact_date.strftime("%Y-%m-%d %H:%M"), "Method": e.contact_method,
                        "Response": e.response_status, "Outcome": e.outcome or "", "Notes": e.notes or "",
                    } for e in history]
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                if p.status == "Do Not Contact":
                    st.warning("This prospect is marked Do Not Contact. No new outreach can be recorded.")
                elif st.button("Mark Do Not Contact", key=f"dnc_{p.id}"):
                    with get_session() as s2:
                        outreach_service.set_do_not_contact(s2, s2.get(Prospect, p.id))
                    st.success("Marked Do Not Contact.")
                    st.rerun()

with tab_record:
    with get_session() as session:
        prospects = session.scalars(select(Prospect).where(Prospect.status != "Do Not Contact").order_by(Prospect.username)).all()
        campaigns = session.scalars(select(Campaign).order_by(Campaign.name)).all()
        if not prospects or not campaigns:
            st.info("Need at least one contactable prospect and one campaign.")
        else:
            prospect_options = {f"@{p.username} ({p.status})": p.id for p in prospects}
            campaign_options = {c.name: c.id for c in campaigns}
            with st.form("record_outreach", clear_on_submit=True):
                c1, c2 = st.columns(2)
                prospect_label = c1.selectbox("Prospect", list(prospect_options.keys()))
                campaign_label = c2.selectbox("Campaign", list(campaign_options.keys()))
                c3, c4 = st.columns(2)
                contact_method = c3.selectbox("Contact method", ["Instagram DM", "Instagram comment reply", "Email", "Other"])
                response_status = c4.selectbox("Response status", ["No response", "Replied", "Positive", "Negative", "Converted"])
                outcome = st.text_input("Outcome (optional)")
                notes = st.text_area("Notes (optional)")
                if st.form_submit_button("Record outreach", type="primary"):
                    try:
                        with get_session() as s2:
                            prospect = s2.get(Prospect, prospect_options[prospect_label])
                            outreach_service.record_event(
                                s2, prospect, campaign_options[campaign_label],
                                contact_method=contact_method, response_status=response_status,
                                outcome=outcome.strip() or None, notes=notes.strip() or None,
                            )
                        st.success("Outreach recorded.")
                        st.rerun()
                    except outreach_service.DoNotContactError as e:
                        st.error(str(e))

with tab_followups:
    with get_session() as session:
        due = followups_service.due_tasks(session)
        upcoming = followups_service.upcoming_tasks(session)

        st.subheader(f"Due or overdue ({len(due)})")
        if not due:
            st.caption("Nothing due.")
        for t in due:
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"@{t.prospect.username} · due {t.due_date:%Y-%m-%d} · {t.notes or ''}")
            if c2.button("Mark done", key=f"done_{t.id}"):
                with get_session() as s2:
                    followups_service.mark_done(s2, s2.get(FollowUpTask, t.id))
                st.rerun()
            if c3.button("Skip", key=f"skip_{t.id}"):
                with get_session() as s2:
                    followups_service.mark_skipped(s2, s2.get(FollowUpTask, t.id))
                st.rerun()

        st.subheader(f"Upcoming ({len(upcoming)})")
        if not upcoming:
            st.caption("Nothing scheduled.")
        for t in upcoming:
            st.write(f"@{t.prospect.username} · due {t.due_date:%Y-%m-%d} · {t.notes or ''}")

    st.divider()
    st.subheader("Schedule a follow-up")
    with get_session() as session:
        prospects = session.scalars(select(Prospect).where(Prospect.status != "Do Not Contact").order_by(Prospect.username)).all()
        campaigns = session.scalars(select(Campaign).order_by(Campaign.name)).all()
    if prospects and campaigns:
        prospect_options = {f"@{p.username}": p.id for p in prospects}
        campaign_options = {c.name: c.id for c in campaigns}
        with st.form("schedule_followup", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            prospect_label = c1.selectbox("Prospect", list(prospect_options.keys()))
            campaign_label = c2.selectbox("Campaign", list(campaign_options.keys()))
            due = c3.date_input("Due date", value=date.today())
            notes = st.text_input("Notes (optional)")
            if st.form_submit_button("Schedule"):
                try:
                    with get_session() as s2:
                        prospect = s2.get(Prospect, prospect_options[prospect_label])
                        due_dt = datetime.combine(due, time(9, 0), tzinfo=timezone.utc)
                        followups_service.schedule_follow_up(s2, prospect, campaign_options[campaign_label], due_dt, notes.strip() or None)
                    st.success("Follow-up scheduled.")
                    st.rerun()
                except outreach_service.DoNotContactError as e:
                    st.error(str(e))
