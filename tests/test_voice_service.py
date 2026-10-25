import pytest
from src.models import Campaign
from src.services import voice as voice_service


@pytest.fixture(autouse=True)
def isolated_audio_dir(tmp_path, monkeypatch):
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    monkeypatch.setattr(voice_service, "AUDIO_DIRECTORY", audio_dir)
    return audio_dir


@pytest.fixture()
def campaign(db_session):
    c = Campaign(name="Voice Test Campaign", product_service="Widgets", objective="Book a demo")
    db_session.add(c)
    db_session.flush()
    return c


def test_generate_voice_asset_calls_tts_and_persists(db_session, campaign, isolated_audio_dir, monkeypatch):
    monkeypatch.setattr(voice_service, "generate_speech", lambda text, voice=None: b"FAKE_MP3_BYTES")
    asset = voice_service.generate_voice_asset(db_session, campaign, "Hello, check out our widgets!", voice="nova")

    assert asset.source == "generated"
    assert asset.voice == "nova"
    stored_path = isolated_audio_dir / asset.stored_filename
    assert stored_path.exists()
    assert stored_path.read_bytes() == b"FAKE_MP3_BYTES"


def test_generate_voice_asset_rejects_empty_script(db_session, campaign, isolated_audio_dir):
    with pytest.raises(voice_service.VoiceAssetError):
        voice_service.generate_voice_asset(db_session, campaign, "   ")


def test_save_uploaded_voice_asset_rejects_bad_extension(db_session, campaign, isolated_audio_dir):
    with pytest.raises(voice_service.VoiceAssetError):
        voice_service.save_uploaded_voice_asset(db_session, campaign, b"data", "recording.exe")


def test_save_uploaded_voice_asset_rejects_oversized_file(db_session, campaign, isolated_audio_dir, monkeypatch):
    monkeypatch.setattr(voice_service, "MAX_UPLOAD_SIZE_MB", 1)
    data = b"0" * (2 * 1024 * 1024)
    with pytest.raises(voice_service.VoiceAssetError):
        voice_service.save_uploaded_voice_asset(db_session, campaign, data, "big.mp3")


def test_save_uploaded_voice_asset_stores_file(db_session, campaign, isolated_audio_dir):
    asset = voice_service.save_uploaded_voice_asset(db_session, campaign, b"real-audio-bytes", "recording.wav")
    assert asset.source == "uploaded"
    assert (isolated_audio_dir / asset.stored_filename).exists()


def test_delete_voice_asset_removes_file(db_session, campaign, isolated_audio_dir):
    asset = voice_service.save_uploaded_voice_asset(db_session, campaign, b"bytes", "r.mp3")
    path = isolated_audio_dir / asset.stored_filename
    assert path.exists()
    voice_service.delete_voice_asset(db_session, asset)
    assert not path.exists()
