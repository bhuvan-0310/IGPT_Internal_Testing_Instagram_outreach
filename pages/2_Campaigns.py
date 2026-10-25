import pandas as pd
import streamlit as st
from sqlalchemy import select
from src.database import get_session
from src.models import Campaign, Prospect
from src.ui import page_header, require_database

st.set_page_config(page_title="Campaigns | Outreach Studio", layout="wide")
require_database()
page_header("Campaigns", "Define campaign context before drafting messages.")

with st.form("create_campaign", clear_on_submit=True):
    name = st.text_input("Campaign name *")
    product = st.text_input("Product or service")
    audience = st.text_area("Target audience / qualification criteria")
    objective = st.text_area("Campaign objective")
    preset = st.text_input("Message preset (optional)")
    submitted = st.form_submit_button("Create campaign", type="primary")
    if submitted:
        if not name.strip():
            st.error("Campaign name is required.")
        else:
            try:
                with get_session() as session:
                    session.add(Campaign(name=name.strip(), product_service=product.strip() or None,
                                         audience=audience.strip() or None, objective=objective.strip() or None,
                                         message_preset=preset.strip() or None, status="Draft"))
                st.success("Campaign created.")
                st.rerun()
            except Exception as e:
                st.error(f"Could not create campaign. Check whether the name already exists. Details: {e}")

st.divider()
with get_session() as session:
    campaigns = session.scalars(select(Campaign).order_by(Campaign.created_at.desc())).all()
    if campaigns:
        rows = []
        for c in campaigns:
            count = len(c.prospects)
            rows.append({"ID": c.id, "Name": c.name, "Product/service": c.product_service or "",
                         "Objective": c.objective or "", "Status": c.status, "Prospects": count})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        selected_id = st.selectbox("Campaign details", [c.id for c in campaigns], format_func=lambda x: next(c.name for c in campaigns if c.id == x))
        selected = next(c for c in campaigns if c.id == selected_id)
        with st.form("update_campaign"):
            status = st.selectbox("Status", ["Draft", "Ready", "Active", "Paused", "Completed", "Archived"],
                                  index=["Draft", "Ready", "Active", "Paused", "Completed", "Archived"].index(selected.status) if selected.status in ["Draft", "Ready", "Active", "Paused", "Completed", "Archived"] else 0)
            if st.form_submit_button("Update campaign status"):
                selected.status = status
                st.success("Campaign status updated.")
                st.rerun()
    else:
        st.info("No campaigns yet. Create your first campaign above.")
