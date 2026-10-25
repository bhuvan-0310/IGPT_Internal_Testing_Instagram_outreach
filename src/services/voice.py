"""Voice Studio: script creation, TTS generation, upload handling, metadata."""
import uuid
from pathlib import Path
from sqlalchemy.orm import Session
from src.config import AUDIO_DIRECTORY, MAX_UPLOAD_SIZE_MB, OPENAI_AUDIO_MODEL, OPENAI_TTS_VOICE
from src.integrations.openai_client import generate_speech
from src.models import Campaign, MessageDraft, VoiceAsset

ALLOWED_UPLOAD_EXTENSIONS = {".mp3", ".wav", ".m4a"}


class VoiceAssetError(ValueError):
    pass


def script_from_draft(draft: MessageDraft) -> str:
    return draft.content


def script_from_campaign(campaign: Campaign) -> str:
    parts = [p for p in [campaign.objective, campaign.product_service] if p]
    return " ".join(parts) or f"Message about {campaign.name}."


def generate_voice_asset(session: Session, campaign: Campaign, script_text: str, voice: str | None = None,
                          source_draft_id: int | None = None) -> VoiceAsset:
    if not script_text or not script_text.strip():
        raise VoiceAssetError("Script text is required.")
    audio_bytes = generate_speech(script_text, voice=voice)
    stored_filename = f"{uuid.uuid4().hex}.mp3"
    target = (AUDIO_DIRECTORY / stored_filename).resolve()
    if AUDIO_DIRECTORY.resolve() not in target.parents:
        raise VoiceAssetError("Resolved storage path escaped the audio directory.")
    target.write_bytes(audio_bytes)

    asset = VoiceAsset(
        campaign_id=campaign.id, source_draft_id=source_draft_id, script_text=script_text,
        voice=voice or OPENAI_TTS_VOICE, model_name=OPENAI_AUDIO_MODEL, source="generated",
        stored_filename=stored_filename, content_type="audio/mpeg", file_size_bytes=len(audio_bytes),
    )
    session.add(asset)
    session.flush()
    return asset


def save_uploaded_voice_asset(session: Session, campaign: Campaign, data: bytes, original_filename: str,
                               script_text: str = "") -> VoiceAsset:
    ext = Path(original_filename or "").suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise VoiceAssetError(f"'{ext or '(no extension)'}' is not allowed. Use mp3, wav, or m4a.")
    max_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(data) > max_bytes:
        raise VoiceAssetError(f"File is {len(data) / 1_048_576:.1f} MB; the limit is {MAX_UPLOAD_SIZE_MB} MB.")

    stored_filename = f"{uuid.uuid4().hex}{ext}"
    target = (AUDIO_DIRECTORY / stored_filename).resolve()
    if AUDIO_DIRECTORY.resolve() not in target.parents:
        raise VoiceAssetError("Resolved storage path escaped the audio directory.")
    target.write_bytes(data)

    asset = VoiceAsset(
        campaign_id=campaign.id, script_text=script_text or "(uploaded recording, no script)",
        source="uploaded", stored_filename=stored_filename, original_filename=original_filename,
        content_type=f"audio/{ext.lstrip('.')}", file_size_bytes=len(data),
    )
    session.add(asset)
    session.flush()
    return asset


def delete_voice_asset(session: Session, asset: VoiceAsset):
    path = (AUDIO_DIRECTORY / asset.stored_filename).resolve()
    if AUDIO_DIRECTORY.resolve() in path.parents and path.exists():
        path.unlink()
    session.delete(asset)


def file_path_for(asset: VoiceAsset) -> Path:
    return AUDIO_DIRECTORY / asset.stored_filename
