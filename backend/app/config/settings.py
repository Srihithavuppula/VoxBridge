# backend/app/config/settings.py
"""
Centralised application settings.
Values are read from environment variables (or a .env file via python-dotenv).
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ── App ────────────────────────────────────────────────────────────────
    APP_NAME: str = "Multilingual Speech Translation System"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # ── CORS ───────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ── Translation ────────────────────────────────────────────────────────
    # Options: auto | googletrans | libretranslate | google | openai
    TRANSLATION_PROVIDER: str = "auto"

    # Google Translate (paid)
    GOOGLE_API_KEY: str = ""

    # OpenAI (paid)
    OPENAI_API_KEY: str = ""

    # LibreTranslate (free — public instance, no key needed)
    LIBRE_TRANSLATE_URL: str = "https://libretranslate.com/translate"
    LIBRE_TRANSLATE_API_KEY: str = ""

    # ── STT (Whisper) ──────────────────────────────────────────────────────
    WHISPER_MODEL_SIZE: str = "base"   # tiny | base | small | medium | large

    # ── TTS ────────────────────────────────────────────────────────────────
    TTS_PROVIDER: str = "gtts"         # gtts | polly

    # AWS Polly (optional)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Singleton instance imported everywhere
settings = Settings()