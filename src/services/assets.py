"""Asset library file handling: validated uploads, safe storage, metadata.

Security notes:
- Filenames are never derived from user input directly; we generate a random
  token + a sanitized extension, so path traversal and collisions are not
  possible.
- File type is validated against an explicit allowlist (by extension and by
  the asset_type the user selected), not trusted from the browser-supplied
  content type alone.
- Size is capped by MAX_UPLOAD_SIZE_MB.
"""
import uuid
from pathlib import Path
from sqlalchemy.orm import Session
from src.config import ASSET_DIRECTORY, MAX_UPLOAD_SIZE_MB
from src.models import Asset

ALLOWED_EXTENSIONS = {
    "pdf": {".pdf"},
    "image": {".png", ".jpg", ".jpeg", ".gif", ".webp"},
    "audio": {".mp3", ".wav", ".m4a"},
}


class AssetValidationError(ValueError):
    pass


def _safe_extension(original_filename: str, asset_type: str) -> str:
    ext = Path(original_filename or "").suffix.lower()
    allowed = ALLOWED_EXTENSIONS.get(asset_type, set())
    if ext not in allowed:
        raise AssetValidationError(
            f"'{ext or '(no extension)'}' is not an allowed file type for {asset_type}. "
            f"Allowed: {', '.join(sorted(allowed))}"
        )
    return ext


def validate_size(size_bytes: int):
    max_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if size_bytes > max_bytes:
        raise AssetValidationError(f"File is {size_bytes / 1_048_576:.1f} MB; the limit is {MAX_UPLOAD_SIZE_MB} MB.")


def store_file_bytes(data: bytes, original_filename: str, asset_type: str) -> tuple[str, str]:
    """Validate and write bytes under ASSET_DIRECTORY with a random safe
    filename. Returns (stored_filename, extension)."""
    validate_size(len(data))
    ext = _safe_extension(original_filename, asset_type)
    stored_name = f"{uuid.uuid4().hex}{ext}"
    target = (ASSET_DIRECTORY / stored_name).resolve()
    if ASSET_DIRECTORY.resolve() not in target.parents:
        raise AssetValidationError("Resolved storage path escaped the asset directory.")
    target.write_bytes(data)
    return stored_name, ext


def create_asset(
    session: Session, *, name: str, description: str | None, asset_type: str,
    campaign_id: int | None, product_url: str | None, tags: str | None, notes: str | None,
    file_bytes: bytes | None = None, original_filename: str | None = None, content_type: str | None = None,
) -> Asset:
    if asset_type == "link":
        if not product_url or not product_url.strip():
            raise AssetValidationError("A product/catalogue URL is required for link assets.")
        asset = Asset(
            name=name, description=description, asset_type="link", campaign_id=campaign_id,
            product_url=product_url.strip(), tags=tags, notes=notes,
        )
    else:
        if not file_bytes:
            raise AssetValidationError("A file is required for this asset type.")
        stored_filename, _ = store_file_bytes(file_bytes, original_filename or "", asset_type)
        asset = Asset(
            name=name, description=description, asset_type=asset_type, campaign_id=campaign_id,
            stored_filename=stored_filename, original_filename=original_filename,
            content_type=content_type, file_size_bytes=len(file_bytes), tags=tags, notes=notes,
        )
    session.add(asset)
    session.flush()
    return asset


def delete_asset(session: Session, asset: Asset):
    if asset.stored_filename:
        path = (ASSET_DIRECTORY / asset.stored_filename).resolve()
        if ASSET_DIRECTORY.resolve() in path.parents and path.exists():
            path.unlink()
    session.delete(asset)


def file_path_for(asset: Asset) -> Path | None:
    if not asset.stored_filename:
        return None
    return ASSET_DIRECTORY / asset.stored_filename
