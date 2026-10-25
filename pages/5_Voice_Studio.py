import streamlit as st
from sqlalchemy import select
from src.database import get_session
from src.models import Campaign, MessageDraft, VoiceAsset
from src.services import voice as voice_service
from src.integrations.openai_client import OpenAINotConfigured, OpenAIRequestFailed
from src.ui import page_header, require_database

st.set_page_config(page_title="Voice Studio | Outreach Studio", layout="wide")
require_database()
page_header("Voice Studio", "Turn an approved message or campaign brief into a voice script, then generate or upload audio. Audio is a managed asset — it is never sent automatically.")

with get_session() as session:
    campaigns = session.scalars(select(Campaign).order_by(Campaign.name)).all()
    if not campaigns:
        st.info("Create a campaign first.")
        st.stop()
    campaign_options = {c.name: c.id for c in campaigns}

campaign_label = st.selectbox("Campaign", list(campaign_options.keys()))
campaign_id = campaign_options[campaign_label]

with get_session() as session:
    campaign = session.get(Campaign, campaign_id)
    approved_drafts = session.scalars(
        select(MessageDraft).where(MessageDraft.campaign_id == campaign_id, MessageDraft.status == "Approved")
    ).all()

st.subheader("1. Build a script")
script_source = st.radio("Start from", ["Approved message draft", "Campaign brief", "Write from scratch"], horizontal=True)
default_script = ""
if script_source == "Approved message draft" and approved_drafts:
    draft_label = st.selectbox("Approved draft", [f"#{d.id} variant {d.variant_label} (@{d.prospect.username})" for d in approved_drafts])
    chosen = approved_drafts[[f"#{d.id} variant {d.variant_label} (@{d.prospect.username})" for d in approved_drafts].index(draft_label)]
    default_script = voice_service.script_from_draft(chosen)
elif script_source == "Campaign brief":
    default_script = voice_service.script_from_campaign(campaign)
elif script_source == "Approved message draft" and not approved_drafts:
    st.caption("No approved drafts yet for this campaign. Approve one in Message Studio, or choose another source.")

script_text = st.text_area("Voice script (editable)", value=default_script, height=140)

st.subheader("2. Generate audio")
c1, c2 = st.columns(2)
voice_choice = c1.selectbox("Voice", ["alloy", "echo", "fable", "onyx", "nova", "shimmer"])
if c2.button("Generate audio", type="primary"):
    try:
        with get_session() as session:
            campaign = session.get(Campaign, campaign_id)
            voice_service.generate_voice_asset(session, campaign, script_text, voice=voice_choice)
        st.success("Audio generated and saved to the asset library below.")
        st.rerun()
    except voice_service.VoiceAssetError as e:
        st.error(str(e))
    except OpenAINotConfigured as e:
        st.error(str(e))
    except OpenAIRequestFailed as e:
        st.error(str(e))

st.subheader("3. Or upload an existing recording")
uploaded = st.file_uploader("Upload audio", type=["mp3", "wav", "m4a"])
if uploaded and st.button("Save uploaded recording"):
    try:
        with get_session() as session:
            campaign = session.get(Campaign, campaign_id)
            voice_service.save_uploaded_voice_asset(session, campaign, uploaded.getvalue(), uploaded.name, script_text)
        st.success("Recording saved.")
        st.rerun()
    except voice_service.VoiceAssetError as e:
        st.error(str(e))

st.divider()
st.subheader(f"Voice assets for '{campaign_label}'")
with get_session() as session:
    voice_assets = session.scalars(
        select(VoiceAsset).where(VoiceAsset.campaign_id == campaign_id).order_by(VoiceAsset.created_at.desc())
    ).all()
    if not voice_assets:
        st.info("No voice assets yet for this campaign.")
    for va in voice_assets:
        with st.container(border=True):
            st.caption(f"{'🎙️ Generated' if va.source == 'generated' else '📁 Uploaded'} · {va.created_at:%Y-%m-%d %H:%M}" + (f" · voice: {va.voice}" if va.voice else ""))
            path = voice_service.file_path_for(va)
            if path.exists():
                st.audio(str(path))
                with open(path, "rb") as f:
                    st.download_button("Download", f.read(), file_name=va.original_filename or va.stored_filename, key=f"dlv_{va.id}")
            else:
                st.warning("Audio file is missing from disk.")
            with st.expander("Script"):
                st.text(va.script_text)
            if st.button("Delete", key=f"delv_{va.id}"):
                with get_session() as s2:
                    voice_service.delete_voice_asset(s2, s2.get(VoiceAsset, va.id))
                st.success("Deleted.")
                st.rerun()
