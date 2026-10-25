import streamlit as st
from sqlalchemy import select
from src.database import get_session
from src.models import Campaign, MessageDraft, Prospect, SkillProfile
from src.services import drafts as drafts_service
from src.services import skills as skills_service
from src.integrations.openai_client import OpenAINotConfigured, OpenAIRequestFailed
from src.ui import page_header, require_database

st.set_page_config(page_title="Message Studio | Outreach Studio", layout="wide")
require_database()
page_header("Message Studio", "Draft, edit, regenerate, and review AI-assisted outreach messages. Approving a draft means it is cleared for manual use — it does not send anything.")

with get_session() as session:
    skills_service.seed_default_profile(session)
    prospects = session.scalars(select(Prospect).order_by(Prospect.username)).all()
    campaigns = session.scalars(select(Campaign).order_by(Campaign.name)).all()
    profiles = skills_service.list_profiles(session)
    prospect_options = {f"@{p.username} (#{p.id}, {p.status})": p.id for p in prospects}
    campaign_options = {c.name: c.id for c in campaigns}
    profile_options = {p.name: p.id for p in profiles}

if not prospects or not campaigns:
    st.info("Import at least one prospect and create a campaign before drafting messages.")
    st.stop()

with st.form("generate_form"):
    c1, c2, c3 = st.columns(3)
    prospect_label = c1.selectbox("Prospect", list(prospect_options.keys()))
    campaign_label = c2.selectbox("Campaign", list(campaign_options.keys()))
    profile_label = c3.selectbox("Skill profile", list(profile_options.keys()))

    c4, c5, c6, c7 = st.columns(4)
    tone = c4.selectbox("Tone", ["friendly", "professional", "casual", "enthusiastic", "warm"])
    language = c5.selectbox("Language", ["English", "Spanish", "Portuguese", "French", "Hindi", "German"])
    length_preset = c6.selectbox("Length", ["short", "medium", "long"])
    variant_count = c7.number_input("Variants", min_value=1, max_value=5, value=3)

    submitted = st.form_submit_button("Generate draft variants", type="primary")

if submitted:
    prospect_id = prospect_options[prospect_label]
    campaign_id = campaign_options[campaign_label]
    profile_id = profile_options[profile_label]
    try:
        with get_session() as session:
            prospect = session.get(Prospect, prospect_id)
            campaign = session.get(Campaign, campaign_id)
            skill_profile = session.get(SkillProfile, profile_id)
            drafts_service.generate_variants(
                session, prospect, campaign, skill_profile,
                tone=tone, language=language, length_preset=length_preset, variant_count=int(variant_count),
            )
        st.success("Generated new draft variants below.")
    except OpenAINotConfigured as e:
        st.error(str(e))
    except OpenAIRequestFailed as e:
        st.error(str(e))

st.divider()

sel_c1, sel_c2 = st.columns(2)
view_prospect_label = sel_c1.selectbox("View drafts for prospect", list(prospect_options.keys()), key="view_prospect")
view_campaign_label = sel_c2.selectbox("View drafts for campaign", list(campaign_options.keys()), key="view_campaign")
view_prospect_id = prospect_options[view_prospect_label]
view_campaign_id = campaign_options[view_campaign_label]

with get_session() as session:
    current_variants = drafts_service.current_variants_for(session, view_prospect_id, view_campaign_id)
    if not current_variants:
        st.info("No drafts yet for this prospect/campaign. Generate some above.")
    for draft in current_variants:
        status_emoji = {"Draft": "📝", "Approved": "✅", "Rejected": "🚫"}.get(draft.status, "📝")
        with st.container(border=True):
            st.markdown(f"**Variant {draft.variant_label}** · v{draft.version} · {status_emoji} {draft.status} · model: `{draft.model_name or '—'}`")
            edited = st.text_area("Content", value=draft.content, key=f"content_{draft.id}", height=120)

            bc1, bc2, bc3, bc4, bc5 = st.columns(5)
            if bc1.button("Save edit", key=f"save_{draft.id}"):
                with get_session() as s2:
                    drafts_service.save_edit(s2, s2.get(MessageDraft, draft.id), edited)
                st.success("Saved.")
                st.rerun()
            if bc2.button("Regenerate", key=f"regen_{draft.id}"):
                try:
                    with get_session() as s2:
                        drafts_service.regenerate_variant(s2, s2.get(MessageDraft, draft.id))
                    st.success("Regenerated as a new version.")
                    st.rerun()
                except (OpenAINotConfigured, OpenAIRequestFailed) as e:
                    st.error(str(e))
            if bc3.button("Approve", key=f"approve_{draft.id}", type="primary"):
                with get_session() as s2:
                    drafts_service.set_status(s2, s2.get(MessageDraft, draft.id), "Approved")
                st.success("Approved for manual use. This does not send anything.")
                st.rerun()
            if bc4.button("Reject", key=f"reject_{draft.id}"):
                with get_session() as s2:
                    drafts_service.set_status(s2, s2.get(MessageDraft, draft.id), "Rejected")
                st.rerun()
            with bc5.popover("History"):
                history = drafts_service.version_history(session, draft)
                for h in history:
                    st.caption(f"v{h.version} · {h.status} · {h.created_at:%Y-%m-%d %H:%M}")
                    st.text(h.content)
