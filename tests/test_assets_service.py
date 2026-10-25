import pytest
from src.services import assets as assets_service


@pytest.fixture(autouse=True)
def isolated_asset_dir(tmp_path, monkeypatch):
    asset_dir = tmp_path / "assets"
    asset_dir.mkdir()
    monkeypatch.setattr(assets_service, "ASSET_DIRECTORY", asset_dir)
    return asset_dir


def test_create_pdf_asset_stores_file_with_random_safe_name(db_session, isolated_asset_dir):
    asset = assets_service.create_asset(
        db_session, name="Catalogue", description=None, asset_type="pdf", campaign_id=None,
        product_url=None, tags=None, notes=None, file_bytes=b"%PDF-1.4 fake",
        original_filename="../../etc/passwd.pdf", content_type="application/pdf",
    )
    assert asset.stored_filename != "../../etc/passwd.pdf"
    assert asset.stored_filename.endswith(".pdf")
    stored_path = isolated_asset_dir / asset.stored_filename
    assert stored_path.exists()
    assert stored_path.parent == isolated_asset_dir


def test_rejects_disallowed_extension_for_asset_type(db_session, isolated_asset_dir):
    with pytest.raises(assets_service.AssetValidationError):
        assets_service.create_asset(
            db_session, name="Bad file", description=None, asset_type="pdf", campaign_id=None,
            product_url=None, tags=None, notes=None, file_bytes=b"not a pdf",
            original_filename="script.exe", content_type="application/octet-stream",
        )


def test_rejects_oversized_file(db_session, isolated_asset_dir, monkeypatch):
    monkeypatch.setattr(assets_service, "MAX_UPLOAD_SIZE_MB", 1)
    big_data = b"0" * (2 * 1024 * 1024)
    with pytest.raises(assets_service.AssetValidationError):
        assets_service.create_asset(
            db_session, name="Huge", description=None, asset_type="image", campaign_id=None,
            product_url=None, tags=None, notes=None, file_bytes=big_data,
            original_filename="big.png", content_type="image/png",
        )


def test_link_asset_requires_url(db_session, isolated_asset_dir):
    with pytest.raises(assets_service.AssetValidationError):
        assets_service.create_asset(
            db_session, name="No URL", description=None, asset_type="link", campaign_id=None,
            product_url="   ", tags=None, notes=None,
        )


def test_link_asset_does_not_touch_filesystem(db_session, isolated_asset_dir):
    asset = assets_service.create_asset(
        db_session, name="Catalogue page", description=None, asset_type="link", campaign_id=None,
        product_url="https://example.com/catalogue", tags=None, notes=None,
    )
    assert asset.stored_filename is None
    assert list(isolated_asset_dir.iterdir()) == []


def test_delete_asset_removes_file_from_disk(db_session, isolated_asset_dir):
    asset = assets_service.create_asset(
        db_session, name="Temp", description=None, asset_type="image", campaign_id=None,
        product_url=None, tags=None, notes=None, file_bytes=b"fake-png-bytes",
        original_filename="pic.png", content_type="image/png",
    )
    stored_path = isolated_asset_dir / asset.stored_filename
    assert stored_path.exists()
    assets_service.delete_asset(db_session, asset)
    assert not stored_path.exists()
