# backend/app/services/translation_service.py
"""
Translation Service
-------------------
Abstracts away the actual translation provider so routes stay clean.

Supported providers:
  • googletrans    – unofficial Google Translate scraper (free, no key)
  • libretranslate – open-source free API (no key needed)
  • auto           – tries googletrans first, falls back to libretranslate
  • google         – google-cloud-translate (paid, needs API key)
  • openai         – GPT-4o via chat completion (paid, needs API key)

Add new providers by subclassing BaseTranslator and registering in
TranslationService.get_provider().
"""

from __future__ import annotations

import abc
import asyncio
import logging
from typing import Optional

from app.config.settings import settings

logger = logging.getLogger(__name__)

# LibreTranslate does not support these language codes
LIBRE_UNSUPPORTED = {"ceb", "co", "fy", "haw", "hmn", "iw", "jv", "la",
                     "lb", "mg", "mi", "ny", "or", "rw", "sm", "gd", "st",
                     "sn", "sd", "su", "tl", "tt", "tk", "ug", "xh", "yi", "yo", "zu"}


# ── Shared language map (extend as needed) ─────────────────────────────────

SUPPORTED_LANGUAGES: dict[str, str] = {
    "af": "Afrikaans", "sq": "Albanian", "am": "Amharic", "ar": "Arabic",
    "hy": "Armenian", "az": "Azerbaijani", "eu": "Basque", "be": "Belarusian",
    "bn": "Bengali", "bs": "Bosnian", "bg": "Bulgarian", "ca": "Catalan",
    "ceb": "Cebuano", "zh": "Chinese (Simplified)", "zh-TW": "Chinese (Traditional)",
    "co": "Corsican", "hr": "Croatian", "cs": "Czech", "da": "Danish",
    "nl": "Dutch", "en": "English", "eo": "Esperanto", "et": "Estonian",
    "fi": "Finnish", "fr": "French", "fy": "Frisian", "gl": "Galician",
    "ka": "Georgian", "de": "German", "el": "Greek", "gu": "Gujarati",
    "ht": "Haitian Creole", "ha": "Hausa", "haw": "Hawaiian", "iw": "Hebrew",
    "hi": "Hindi", "hmn": "Hmong", "hu": "Hungarian", "is": "Icelandic",
    "ig": "Igbo", "id": "Indonesian", "ga": "Irish", "it": "Italian",
    "ja": "Japanese", "jv": "Javanese", "kn": "Kannada", "kk": "Kazakh",
    "km": "Khmer", "rw": "Kinyarwanda", "ko": "Korean", "ku": "Kurdish",
    "ky": "Kyrgyz", "lo": "Lao", "la": "Latin", "lv": "Latvian",
    "lt": "Lithuanian", "lb": "Luxembourgish", "mk": "Macedonian",
    "mg": "Malagasy", "ms": "Malay", "ml": "Malayalam", "mt": "Maltese",
    "mi": "Maori", "mr": "Marathi", "mn": "Mongolian", "my": "Myanmar (Burmese)",
    "ne": "Nepali", "no": "Norwegian", "ny": "Nyanja (Chichewa)",
    "or": "Odia (Oriya)", "ps": "Pashto", "fa": "Persian", "pl": "Polish",
    "pt": "Portuguese", "pa": "Punjabi", "ro": "Romanian", "ru": "Russian",
    "sm": "Samoan", "gd": "Scots Gaelic", "sr": "Serbian", "st": "Sesotho",
    "sn": "Shona", "sd": "Sindhi", "si": "Sinhala", "sk": "Slovak",
    "sl": "Slovenian", "so": "Somali", "es": "Spanish", "su": "Sundanese",
    "sw": "Swahili", "sv": "Swedish", "tl": "Tagalog (Filipino)",
    "tg": "Tajik", "ta": "Tamil", "tt": "Tatar", "te": "Telugu",
    "th": "Thai", "tr": "Turkish", "tk": "Turkmen", "uk": "Ukrainian",
    "ur": "Urdu", "ug": "Uyghur", "uz": "Uzbek", "vi": "Vietnamese",
    "cy": "Welsh", "xh": "Xhosa", "yi": "Yiddish", "yo": "Yoruba",
    "zu": "Zulu",
}


# ── Abstract base ───────────────────────────────────────────────────────────

class BaseTranslator(abc.ABC):
    """Interface every provider must implement."""

    @abc.abstractmethod
    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: str = "auto",
    ) -> tuple[str, str]:
        """Returns (translated_text, detected_source_language)."""


# ── deep-translator provider (FREE, no conflicts) ───────────────────────────

class GoogleTransFreeTranslator(BaseTranslator):
    """
    Uses deep-translator library — FREE, modern, no dependency conflicts.
    Install: pip install deep-translator
    """

    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: str = "auto",
    ) -> tuple[str, str]:
        try:
            from deep_translator import GoogleTranslator  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "deep-translator is not installed. "
                "Run: pip install deep-translator"
            ) from exc

        src = source_language if source_language != "auto" else "auto"

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: GoogleTranslator(source=src, target=target_language).translate(text),
        )

        return result, source_language


# ── LibreTranslate provider (FREE) ─────────────────────────────────────────

class LibreTranslateTranslator(BaseTranslator):
    """
    LibreTranslate public API — FREE, open-source, no key needed.
    Public instance : https://libretranslate.com
    Self-host option: set LIBRE_TRANSLATE_URL in .env
    Install: pip install httpx  (already in requirements.txt)
    """

    DEFAULT_URL = "https://libretranslate.com/translate"

    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: str = "auto",
    ) -> tuple[str, str]:
        try:
            import httpx  # type: ignore
        except ImportError as exc:
            raise RuntimeError("httpx is not installed. Run: pip install httpx") from exc

        if target_language in LIBRE_UNSUPPORTED:
            raise RuntimeError(
                f"LibreTranslate does not support '{target_language}'. "
                "Try provider='googletrans' instead."
            )

        src = source_language if source_language != "auto" else "auto"
        payload: dict = {"q": text, "source": src, "target": target_language, "format": "text"}

        # Optional API key for self-hosted instances that require one
        libre_key = getattr(settings, "LIBRE_TRANSLATE_API_KEY", "")
        if libre_key:
            payload["api_key"] = libre_key

        base_url = getattr(settings, "LIBRE_TRANSLATE_URL", self.DEFAULT_URL)

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(base_url, json=payload)

        if response.status_code != 200:
            raise RuntimeError(
                f"LibreTranslate error {response.status_code}: {response.text}"
            )

        data = response.json()
        translated = data.get("translatedText", "")
        detected = (
            data.get("detectedLanguage", {}).get("language", source_language)
            or source_language
        )
        return translated, detected


# ── Auto provider (googletrans → LibreTranslate fallback) ──────────────────

class AutoTranslator(BaseTranslator):
    """
    Tries googletrans first. On any failure automatically
    falls back to LibreTranslate. No config needed.
    """

    def __init__(self):
        self._primary  = GoogleTransFreeTranslator()
        self._fallback = LibreTranslateTranslator()

    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: str = "auto",
    ) -> tuple[str, str]:
        try:
            result = await self._primary.translate(text, target_language, source_language)
            logger.info("AutoTranslator: used googletrans")
            return result
        except Exception as primary_err:
            logger.warning(
                "AutoTranslator: googletrans failed (%s) — falling back to LibreTranslate",
                primary_err,
            )
            try:
                result = await self._fallback.translate(text, target_language, source_language)
                logger.info("AutoTranslator: used LibreTranslate (fallback)")
                return result
            except Exception as fallback_err:
                raise RuntimeError(
                    f"Both providers failed.\n"
                    f"  googletrans    : {primary_err}\n"
                    f"  libretranslate : {fallback_err}"
                )


# ── Google Cloud provider (paid, kept for future use) ──────────────────────

class GoogleTranslator(BaseTranslator):
    """
    Official google-cloud-translate REST API (v2).
    Requires GOOGLE_API_KEY in .env + billing enabled.
    Install: pip install google-cloud-translate
    """

    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: str = "auto",
    ) -> tuple[str, str]:
        try:
            from google.cloud import translate_v2 as google_translate  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "google-cloud-translate is not installed. "
                "Run: pip install google-cloud-translate"
            ) from exc

        client = google_translate.Client(client_options={"api_key": settings.GOOGLE_API_KEY})
        kwargs: dict = {"target_language": target_language}
        if source_language != "auto":
            kwargs["source_language"] = source_language

        result = client.translate(text, **kwargs)
        detected = result.get("detectedSourceLanguage", source_language)
        return result["translatedText"], detected


# ── OpenAI provider (paid, kept for future use) ────────────────────────────

class OpenAITranslator(BaseTranslator):
    """
    GPT-4o-mini chat completion.
    Requires OPENAI_API_KEY in .env.
    Install: pip install openai
    """

    SYSTEM_PROMPT = (
        "You are a professional translator. "
        "Translate the user's text faithfully, preserving tone and formatting. "
        "Return ONLY the translated text — no explanations, no extra text."
    )

    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: str = "auto",
    ) -> tuple[str, str]:
        try:
            from openai import AsyncOpenAI  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "openai is not installed. Run: pip install openai"
            ) from exc

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        lang_name = SUPPORTED_LANGUAGES.get(target_language, target_language)
        src_hint = (
            "" if source_language == "auto"
            else f" The source language is {SUPPORTED_LANGUAGES.get(source_language, source_language)}."
        )
        user_msg = f"Translate the following text into {lang_name}.{src_hint}\n\n{text}"

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
            temperature=0.2,
        )

        translated = response.choices[0].message.content.strip()
        detected = source_language if source_language != "auto" else "unknown"
        return translated, detected


# ── Service façade ──────────────────────────────────────────────────────────

class TranslationService:
    """Single entry point for all translation operations."""

    _providers: dict[str, BaseTranslator] = {}

    @classmethod
    def get_provider(cls, name: Optional[str] = None) -> BaseTranslator:
        provider_name = (name or settings.TRANSLATION_PROVIDER).lower()

        if provider_name not in cls._providers:
            if provider_name == "googletrans":
                cls._providers[provider_name] = GoogleTransFreeTranslator()
            elif provider_name == "libretranslate":
                cls._providers[provider_name] = LibreTranslateTranslator()
            elif provider_name == "auto":
                cls._providers[provider_name] = AutoTranslator()
            elif provider_name == "google":
                cls._providers[provider_name] = GoogleTranslator()
            elif provider_name == "openai":
                cls._providers[provider_name] = OpenAITranslator()
            else:
                raise ValueError(
                    f"Unknown translation provider '{provider_name}'. "
                    "Choose: auto | googletrans | libretranslate | google | openai"
                )

        return cls._providers[provider_name]

    @classmethod
    async def translate(
        cls,
        text: str,
        target_language: str,
        source_language: str = "auto",
        provider: Optional[str] = None,
    ) -> dict:
        """High-level helper used by route handlers."""
        provider_name = (provider or settings.TRANSLATION_PROVIDER).lower()
        translator = cls.get_provider(provider_name)

        logger.info(
            "Translating %d chars | %s → %s | provider=%s",
            len(text), source_language, target_language, provider_name,
        )

        translated_text, detected_source = await translator.translate(
            text=text,
            target_language=target_language,
            source_language=source_language,
        )

        return {
            "original_text":   text,
            "translated_text": translated_text,
            "source_language": detected_source,
            "target_language": target_language,
            "provider":        provider_name,
            "character_count": len(text),
        }

    @staticmethod
    def get_supported_languages() -> dict[str, str]:
        return SUPPORTED_LANGUAGES