# backend/app/services/pipeline_service.py
"""
Pipeline Service
-----------------
Chains STT → Translation → TTS into a single audio-to-audio operation.
"""

from __future__ import annotations

import logging
import uuid
import os
from pathlib import Path

from app.services.stt_service         import STTService
from app.services.translation_service import TranslationService
from app.services.tts_service         import TTSService

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("tmp_audio")
OUTPUT_DIR.mkdir(exist_ok=True)

# Full backend URL — set this in .env / Render env variables
# e.g. https://voxbridge-backend.onrender.com
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")


class PipelineService:

    @classmethod
    async def run(
        cls,
        audio_bytes: bytes,
        filename: str,
        target_language: str,
        source_language: str = "auto",
        translation_provider: str | None = None,
        tts_provider: str | None = None,
        slow_speech: bool = False,
    ) -> dict:

        # ── Step 1: Speech → Text ──────────────────────────────────────────
        logger.info("Pipeline [1/3] STT starting…")
        stt_result = await STTService.transcribe_bytes(
            audio_bytes=audio_bytes,
            filename=filename,
            language=None if source_language == "auto" else source_language,
        )
        transcript    = stt_result["transcript"]
        detected_lang = stt_result["language"]
        duration      = stt_result["duration"]
        logger.info("Pipeline [1/3] STT done: '%s…' (lang=%s)", transcript[:50], detected_lang)

        # ── Step 2: Text → Translated Text ────────────────────────────────
        logger.info("Pipeline [2/3] Translation starting…")
        translation_result = await TranslationService.translate(
            text=transcript,
            target_language=target_language,
            source_language=detected_lang,   # ✅ use detected lang, not original param
            provider=translation_provider,
        )
        translated_text = translation_result["translated_text"]
        used_provider   = translation_result["provider"]
        logger.info("Pipeline [2/3] Translation done: '%s…'", translated_text[:50])

        # ── Step 3: Translated Text → Speech ──────────────────────────────
        logger.info("Pipeline [3/3] TTS starting…")
        audio_out = await TTSService.synthesize(
            text=translated_text,
            language=target_language,
            slow=slow_speech,
            provider=tts_provider,
        )

        file_id  = uuid.uuid4().hex
        out_path = OUTPUT_DIR / f"{file_id}.mp3"
        out_path.write_bytes(audio_out)
        logger.info("Pipeline [3/3] TTS done, saved to %s", out_path)

        return {
            "original_transcript":  transcript,
            "translated_text":      translated_text,
            "source_language":      detected_lang,
            "target_language":      target_language,
            "translation_provider": used_provider,
            "audio_url":            f"{BASE_URL}/api/v1/audio/download/{file_id}.mp3",  # ✅ full URL
            "duration":             duration,
        }

    @staticmethod
    def get_output_path(filename: str) -> Path | None:
        safe_name = Path(filename).name
        path = OUTPUT_DIR / safe_name
        return path if path.exists() else None