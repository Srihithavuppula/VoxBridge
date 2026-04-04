# backend/app/services/tts_service.py
"""
Text-to-Speech Service
-----------------------
Default provider: gTTS (Google Text-to-Speech) — FREE, no API key needed.
Optional provider: AWS Polly — higher quality, needs AWS credentials.

Install: pip install gTTS
"""

from __future__ import annotations

import io
import asyncio
import logging
from typing import Literal

from app.config.settings import settings

logger = logging.getLogger(__name__)

TTSProvider = Literal["gtts", "polly"]


class TTSService:
    """
    Converts text to speech audio bytes (MP3).
    Returns raw bytes so the route can stream them directly.
    """

    @classmethod
    async def synthesize(
        cls,
        text: str,
        language: str = "en",
        slow: bool = False,
        provider: TTSProvider | None = None,
        auto_translate: bool = True,
    ) -> bytes:
        """
        Convert text to speech in target language.
        If text is not in target language, optionally translate first.
        """

        # Step 1: Auto-translate if needed
        if auto_translate:
            try:
                from app.services.translation_service import TranslationService

                result = await TranslationService.translate(
                    text=text,
                    target_language=language,
                    source_language="auto",
                )
                logger.debug(
                    "Translation result for '%s' to '%s': %s",
                    text[:50], language, result.get("translated_text", "")
                )
                text = result["translated_text"]

            except Exception as e:
                logger.warning(f"Translation failed, using original text: {e}")

        # Step 2: TTS
        if provider is None:
            provider_str = getattr(settings, "TTS_PROVIDER", None)
            if provider_str is None:
                logger.error("TTS provider is not specified and not set in settings")
                raise ValueError("No TTS provider specified")
            chosen = provider_str.lower()
        else:
            chosen = provider.lower()

        logger.debug(f"TTS provider selected: {chosen}")

        if chosen == "gtts":
            return await cls._gtts(text, language, slow)
        elif chosen == "polly":
            return await cls._polly(text, language)
        else:
            logger.error(f"Unknown TTS provider '{chosen}'")
            raise ValueError(f"Unknown TTS provider '{chosen}'")

    # ── gTTS ────────────────────────────────────────────────────────────────

    @classmethod
    async def _gtts(cls, text: str, language: str, slow: bool) -> bytes:
        try:
            from gtts import gTTS  # type: ignore
        except ImportError as exc:
            logger.error("gTTS import failed: %s", exc)
            raise RuntimeError(
                "gTTS is not installed. Run: pip install gTTS"
            ) from exc

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        def _synth():
            logger.debug(f"Calling gTTS with text='{text[:30]}...', language='{language}', slow={slow}")
            tts = gTTS(text=text, lang=language, slow=slow)
            buf = io.BytesIO()
            tts.write_to_fp(buf)
            buf.seek(0)
            return buf.read()

        # gTTS makes an HTTP request — run in thread pool
        try:
            audio_bytes = await loop.run_in_executor(None, _synth)
        except Exception as ex:
            logger.error(f"gTTS synthesis failed: {ex}")
            raise

        logger.info("gTTS synthesised %d chars in '%s'", len(text), language)
        return audio_bytes

    # ── AWS Polly ───────────────────────────────────────────────────────────

    @classmethod
    async def _polly(cls, text: str, language: str) -> bytes:
        try:
            import boto3  # type: ignore
        except ImportError as exc:
            logger.error("boto3 import failed: %s", exc)
            raise RuntimeError(
                "boto3 is not installed. Run: pip install boto3"
            ) from exc

        # Map BCP-47 codes to Polly voice IDs
        POLLY_VOICES: dict[str, str] = {
            "en": "Joanna", "es": "Lucia",  "fr": "Celine",
            "de": "Marlene","it": "Bianca", "pt": "Ines",
            "hi": "Aditi",  "ja": "Mizuki", "ko": "Seoyeon",
            "ar": "Zeina",  "zh": "Zhiyu",  "ru": "Tatyana",
            "pl": "Ewa",    "nl": "Lotte",  "sv": "Astrid",
            "tr": "Filiz",  "ro": "Carmen", "cs": "Jacek",
        }

        voice_id = POLLY_VOICES.get(language, "Joanna")
        logger.debug(f"Using AWS Polly language='{language}' voice_id='{voice_id}'")

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        def _synth():
            logger.debug("Initiating AWS Polly client")
            try:
                client = boto3.client(
                    "polly",
                    region_name=getattr(settings, "AWS_REGION", "us-east-1"),
                    aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
                    aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
                )
                logger.debug(
                    f"Calling Polly.synthesize_speech with text length {len(text)}, voice_id={voice_id}"
                )
                response = client.synthesize_speech(
                    Text=text,
                    OutputFormat="mp3",
                    VoiceId=voice_id,
                )
                audio_data = response["AudioStream"].read()
                logger.debug("Received audio from AWS Polly for %d chars", len(text))
                return audio_data
            except Exception as e:
                logger.error(f"AWS Polly synthesis failed: {e}")
                raise

        try:
            audio_bytes = await loop.run_in_executor(None, _synth)
        except Exception as ex:
            logger.error(f"Polly synthesis failed: {ex}")
            raise

        logger.info("Polly synthesised %d chars, voice=%s", len(text), voice_id)
        return audio_bytes