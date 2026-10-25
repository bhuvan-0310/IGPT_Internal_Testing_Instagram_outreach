import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]

# Load .env from the project root explicitly, regardless of the directory
# `streamlit run` was invoked from.
load_dotenv(BASE_DIR / ".env")

DATA_DIR = Path(os.getenv("DATA_DIRECTORY", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

def validate_database_url(url: str, env_file_path: Path = BASE_DIR / ".env") -> None:
    """Raise RuntimeError with an actionable message if `url` is missing or
    not a PostgreSQL connection string. Pure validation, no I/O, so it can be
    unit tested directly without touching the real .env file."""
    if not url or not url.strip():
        raise RuntimeError(
            f"DATABASE_URL is not set. Copy .env.example to .env in the project root "
            f"({env_file_path}) and set DATABASE_URL to your PostgreSQL connection "
            "string, e.g.\n"
            "DATABASE_URL=postgresql+psycopg://outreach_app:YOUR_PASSWORD@localhost:5432/instagram_outreach"
        )
    if not url.startswith("postgresql"):
        raise RuntimeError(
            "DATABASE_URL must be a PostgreSQL connection string starting with "
            "'postgresql+psycopg://' or 'postgresql://'. SQLite and other drivers "
            "are not supported by this application."
        )


DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
validate_database_url(DATABASE_URL)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-4.1-mini")
OPENAI_AUDIO_MODEL = os.getenv("OPENAI_AUDIO_MODEL", "gpt-4o-mini-tts")
OPENAI_TTS_VOICE = os.getenv("OPENAI_TTS_VOICE", "alloy")
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")
BROWSER_PROFILE_DIR = Path(os.getenv("BROWSER_PROFILE_DIR", DATA_DIR / "browser_profile"))
ASSET_DIRECTORY = Path(os.getenv("ASSET_DIRECTORY", DATA_DIR / "assets"))
AUDIO_DIRECTORY = Path(os.getenv("AUDIO_DIRECTORY", DATA_DIR / "audio"))

MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "25"))

for directory in (ASSET_DIRECTORY, AUDIO_DIRECTORY, BROWSER_PROFILE_DIR):
    directory.mkdir(parents=True, exist_ok=True)


def mask_url(url: str) -> str:
    """Redact the password portion of a connection string, safe for display/logs."""
    if "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    if "@" not in rest:
        return f"{scheme}://{rest}"
    creds, host_part = rest.split("@", 1)
    if ":" in creds:
        user = creds.split(":", 1)[0]
        return f"{scheme}://{user}:****@{host_part}"
    return f"{scheme}://{creds}@{host_part}"


def masked_database_url() -> str:
    """Return DATABASE_URL with the password redacted, safe for display/logs."""
    return mask_url(DATABASE_URL)
