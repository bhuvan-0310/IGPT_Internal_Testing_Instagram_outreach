import json
import pandas as pd
import streamlit as st
from sqlalchemy import select, or_
from src.database import get_session
from src.models import Prospect, Campaign
from src.services import prospects as prospects_service
from src.ui import page_header, require_database

st.set_page_config(page_title="Prospects | Outreach Studio", layout="wide")
require_database()
page_header("Prospects", "Import and manage prospect records. Review imported data before using it in a campaign.")

uploaded = st.file_uploader("Import Apify export, CSV, or Excel", type=["csv", "xlsx", "xls"])
if uploaded:
    try:
        df = pd.read_csv(uploaded) if uploaded.name.lower().endswith(".csv") else pd.read_excel(uploaded)
        st.write("Preview")
        st.dataframe(df.head(20), width="stretch", alt="Preview of imported prospect rows")
        cols = list(df.columns)
        username_guess = prospects_service.guess_username_column(cols)
        username_col = st.selectbox("Column containing Instagram username (required)", cols, index=cols.index(username_guess) if username_guess in cols else 0)
        display_col = st.selectbox("Display name column (optional)", ["— None —"] + cols)
        profile_col = st.selectbox("Profile URL column (optional)", ["— None —"] + cols)
        source_id_col = st.selectbox("Source-specific ID column (optional)", ["— None —"] + cols)
        bio_col = st.selectbox("Bio column (optional)", ["— None —"] + cols)
        reel_col = st.selectbox("Source Reel URL column (optional)", ["— None —"] + cols)
        text_col = st.selectbox("Source comment/text column (optional)", ["— None —"] + cols)
        if st.button("Import rows", type="primary"):
            with get_session() as session:
                result = prospects_service.import_dataframe(
                    session, df, username_col=username_col, display_col=display_col,
                    profile_col=profile_col, source_id_col=source_id_col, bio_col=bio_col,
                    reel_col=reel_col, text_col=text_col,
                )
            st.success(f"Import complete. Added {result.imported}; skipped blank/duplicate rows {result.skipped}.")
    except Exception as e:
        st.error(f"Could not read this file: {e}")

st.divider()
with get_session() as session:
    campaigns = session.scalars(select(Campaign).order_by(Campaign.name)).all()
    campaign_options = {"— Unassigned —": None}
    campaign_options.update({c.name: c.id for c in campaigns})
    c1, c2 = st.columns([2, 1])
    query = c1.text_input("Search username, name, bio or source text")
    statuses = ["New", "Qualified", "Draft Ready", "Approved", "Contacted", "Replied", "Converted", "Not Eligible", "Skipped", "Do Not Contact", "Unresponsive", "Archived"]
    status_filter = c2.multiselect("Status", statuses, default=["New", "Qualified", "Draft Ready", "Approved", "Contacted", "Replied", "Converted"])
    stmt = select(Prospect).order_by(Prospect.created_at.desc())
    if status_filter:
        stmt = stmt.where(Prospect.status.in_(status_filter))
    if query:
        like = f"%{query}%"
        stmt = stmt.where(or_(Prospect.username.ilike(like), Prospect.display_name.ilike(like), Prospect.bio.ilike(like), Prospect.source_text.ilike(like)))
    prospects = session.scalars(stmt.limit(1000)).all()
    st.caption(f"Showing {len(prospects)} matching records (maximum 1,000 in this view).")
    if prospects:
        view = pd.DataFrame([{
            "Select": False,
            "ID": p.id, "Username": p.username, "Display name": p.display_name or "",
            "Status": p.status, "Profile": p.profile_url or "", "Source text": p.source_text or "",
            "Campaign": p.campaign.name if p.campaign else ""
        } for p in prospects])
        selection_version = st.session_state.get("prospect_selection_version", 0)
        selected_view = st.data_editor(
            view,
            column_config={
                "Select": st.column_config.CheckboxColumn("Select", help="Select this prospect for bulk campaign assignment."),
                "Profile": st.column_config.LinkColumn("Profile"),
            },
            disabled=[column for column in view.columns if column != "Select"],
            hide_index=True,
            key=f"prospect_selection_editor_{selection_version}",
            alt="Filtered prospect list with selectable rows",
        )

        selected_ids = selected_view.loc[selected_view["Select"], "ID"].tolist()
        st.subheader("Assign selected prospects to a campaign")
        if not campaigns:
            st.info("Create a campaign before assigning selected prospects.")
        else:
            with st.form("bulk_assign_campaign", border=False):
                target_campaign = st.selectbox("Campaign", [c.name for c in campaigns])
                assign_submitted = st.form_submit_button(
                    f"Assign {len(selected_ids)} selected prospect(s)",
                    type="primary",
                    disabled=not selected_ids,
                )
            if assign_submitted:
                target_campaign_id = next(c.id for c in campaigns if c.name == target_campaign)
                with get_session() as update_session:
                    updated = prospects_service.assign_campaign(update_session, selected_ids, target_campaign_id)
                st.session_state["prospect_selection_version"] = selection_version + 1
                st.success(f"Assigned {updated} prospect(s) to {target_campaign}.")
                st.rerun()

        with st.form("edit_prospect"):
            st.subheader("Update a prospect")
            selected_id = st.selectbox("Prospect", [p.id for p in prospects], format_func=lambda x: next((f"#{p.id} @{p.username}" for p in prospects if p.id == x), str(x)))
            selected = next(p for p in prospects if p.id == selected_id)
            new_status = st.selectbox("Status", statuses, index=statuses.index(selected.status) if selected.status in statuses else 0)
            new_campaign_name = st.selectbox("Campaign", list(campaign_options.keys()), index=(list(campaign_options.values()).index(selected.campaign_id) if selected.campaign_id in campaign_options.values() else 0))
            new_notes = st.text_area("Notes", value=selected.notes or "")
            if st.form_submit_button("Save changes"):
                selected.status = new_status
                selected.campaign_id = campaign_options[new_campaign_name]
                selected.notes = new_notes
                st.success("Prospect updated.")
                st.rerun()
    else:
        st.info("No prospects yet. Import a CSV or Excel file above.")
