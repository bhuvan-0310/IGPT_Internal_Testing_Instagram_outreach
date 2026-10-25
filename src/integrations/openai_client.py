"""Thin wrapper around the OpenAI SDK so the rest of the app never imports it
directly. Keeps API-key/model configuration and error handling in one place.
"""
from src.config import OPENAI_API_KEY, OPENAI_TEXT_MODEL, OPENAI_AUDIO_MODEL, OPENAI_TTS_VOICE


class OpenAINotConfigured(RuntimeError):
    pass


class OpenAIRequestFailed(RuntimeError):
    pass


def _client():
    if not OPENAI_API_KEY:
        raise OpenAINotConfigured(
            "OPENAI_API_KEY is not set in .env. Add your key to enable AI drafting/voice features."
        )
    from openai import OpenAI  # imported lazily so the app works without the package installed yet
    return OpenAI(api_key=OPENAI_API_KEY)


def generate_text(system_prompt: str, user_prompt: str, model: str | None = None) -> str:
    """Call the chat completions API and return the raw text response."""
    client = _client()
    model_name = model or OPENAI_TEXT_MODEL
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as exc:  # noqa: BLE001 - surface a helpful message regardless of SDK exception type
        raise OpenAIRequestFailed(
            f"OpenAI text generation failed using model '{model_name}'. "
            f"Check OPENAI_API_KEY and that your account has access to this model. Details: {exc}"
        ) from exc
    return response.choices[0].message.content or ""


def generate_speech(text: str, voice: str | None = None, model: str | None = None) -> bytes:
    """Call the text-to-speech API and return raw audio bytes (mp3)."""
    client = _client()
    model_name = model or OPENAI_AUDIO_MODEL
    voice_name = voice or OPENAI_TTS_VOICE
    try:
        response = client.audio.speech.create(model=model_name, voice=voice_name, input=text)
    except Exception as exc:  # noqa: BLE001
        raise OpenAIRequestFailed(
            f"OpenAI speech generation failed using model '{model_name}' / voice '{voice_name}'. "
            f"Check OPENAI_API_KEY and model availability. Details: {exc}"
        ) from exc
    return response.read() if hasattr(response, "read") else response.content
