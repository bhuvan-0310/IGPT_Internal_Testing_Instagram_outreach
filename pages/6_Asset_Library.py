import streamlit as st
from sqlalchemy import select
from src.database import get_session
from src.models import Asset, Campaign
from src.services import assets as assets_service
from src.ui import page_header, require_database

st.set_page_config(page_title="Asset Library | Outreach Studio", layout="wide")
require_database()
page_header("Asset Library", "Product facts, PDFs, images, audio, and catalogue links, organized by campaign.")

with get_session() as session:
    campaigns = session.scalars(select(Campaign).order_by(Campaign.name)).all()
    campaign_options = {"— Unassigned —": None}
    campaign_options.update({c.name: c.id for c in campaigns})

st.subheader("Add an asset")
asset_type = st.selectbox("Asset type", ["pdf", "image", "audio", "link"], format_func=lambda x: x.upper())
with st.form("new_asset", clear_on_submit=True):
    name = st.text_input("Name *")
    description = st.text_area("Description")
    campaign_label = st.selectbox("Campaign", list(campaign_options.keys()))
    tags = st.text_input("Tags (comma-separated)")
    notes = st.text_area("Notes")

    product_url = None
    uploaded = None
    if asset_type == "link":
        product_url = st.text_input("Product / catalogue URL *")
    else:
        type_hint = {"pdf": ["pdf"], "image": ["png", "jpg", "jpeg", "gif", "webp"], "audio": ["mp3", "wav", "m4a"]}[asset_type]
        uploaded = st.file_uploader(f"Upload {asset_type} file *", type=type_hint)

    if st.form_submit_button("Save asset", type="primary"):
        if not name.strip():
            st.error("Name is required.")
        else:
            try:
                with get_session() as session:
                    assets_service.create_asset(
                        session, name=name.strip(), description=description.strip() or None,
                        asset_type=asset_type, campaign_id=campaign_options[campaign_label],
                        product_url=product_url, tags=tags.strip() or None, notes=notes.strip() or None,
                        file_bytes=uploaded.getvalue() if uploaded else None,
                        original_filename=uploaded.name if uploaded else None,
                        content_type=uploaded.type if uploaded else None,
                    )
                st.success(f"Asset '{name.strip()}' saved.")
                st.rerun()
            except assets_service.AssetValidationError as e:
                st.error(str(e))

st.divider()
st.subheader("Library")

with get_session() as session:
    filter_type = st.multiselect("Filter by type", ["pdf", "image", "audio", "link"], default=["pdf", "image", "audio", "link"])
    stmt = select(Asset).order_by(Asset.created_at.desc())
    if filter_type:
        stmt = stmt.where(Asset.asset_type.in_(filter_type))
    items = session.scalars(stmt).all()

    if not items:
        st.info("No assets yet. Add one above.")
    for asset in items:
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"**{asset.name}** · `{asset.asset_type.upper()}`" + (f" · campaign: {asset.campaign.name}" if asset.campaign else ""))
            if asset.description:
                c1.caption(asset.description)
            if asset.asset_type == "link":
                c1.markdown(f"[{asset.product_url}]({asset.product_url})")
            elif asset.stored_filename:
                path = assets_service.file_path_for(asset)
                size_kb = (asset.file_size_bytes or 0) / 1024
                c1.caption(f"{asset.original_filename or asset.stored_filename} · {size_kb:.0f} KB")
                if asset.asset_type == "image" and path and path.exists():
                    c1.image(str(path), width=200)
                elif asset.asset_type == "audio" and path and path.exists():
                    c1.audio(str(path))
                elif path and path.exists():
                    with open(path, "rb") as f:
                        c1.download_button("Download", f.read(), file_name=asset.original_filename or asset.stored_filename, key=f"dl_{asset.id}")
            if asset.tags:
                c1.caption(f"Tags: {asset.tags}")
            if c2.button("Delete", key=f"del_{asset.id}"):
                with get_session() as s2:
                    assets_service.delete_asset(s2, s2.get(Asset, asset.id))
                st.success("Deleted.")
                st.rerun()
