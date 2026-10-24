import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("DATA_DIRECTORY", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/instagram_outreach")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-4.1-mini")
OPENAI_AUDIO_MODEL = os.getenv("OPENAI_AUDIO_MODEL", "gpt-4o-mini-tts")
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")
BROWSER_PROFILE_DIR = Path(os.getenv("BROWSER_PROFILE_DIR", DATA_DIR / "browser_profile"))
ASSET_DIRECTORY = Path(os.getenv("ASSET_DIRECTORY", DATA_DIR / "assets"))
AUDIO_DIRECTORY = Path(os.getenv("AUDIO_DIRECTORY", DATA_DIR / "audio"))
for directory in (ASSET_DIRECTORY, AUDIO_DIRECTORY, BROWSER_PROFILE_DIR):
    directory.mkdir(parents=True, exist_ok=True)
