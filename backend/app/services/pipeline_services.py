# backend/app/services/pipeline_service.py
"""
Pipeline Service
-----------------
Chains STT → Translation → TTS into a single audio-to-audio operation.

Flow:
  Audio file
      │
      ▼ STTService.transcribe_bytes()
  Transcript (text + detected language)
      │
      ▼ TranslationService.translate()
  Translated text
      │
      ▼ TTSService.synthesize()
  Output audio (MP3 bytes)
"""

from __future__ import annotations

import logging
import uuid
import os
from pathlib import Path

from app.services.stt_service        import STTService
from app.services.translation_service import TranslationService
from app.services.tts_service        import TTSService

logger = logging.getLogger(__name__)

# Temp directory for synthesised audio files available for download
OUTPUT_DIR = Path("tmp_audio")
OUTPUT_DIR.mkdir(exist_ok=True)

# BASE_URL could be used if you want to prepend a base path for downloads, but here audio_url is hardcoded.
# BASE_URL = os.getenv("BASE_URL", "")
BASE_URL = os.getenv("BASE_URL", "")

class PipelineService:
    """
    Orchestrates the full audio-to-audio translation pipeline.
    """

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
        """
        Run the full pipeline.

        Returns a dict matching PipelineResponse schema.
        """

        # ── Step 1: Speech → Text ──────────────────────────────────────────
        logger.info("Pipeline [1/3] STT starting…")
        stt_result = await STTService.transcribe_bytes(
            audio_bytes=audio_bytes,
            filename=filename,
            language=None if source_language == "auto" else source_language,
        )
        transcript      = stt_result["transcript"]
        detected_lang   = stt_result["language"]
        duration        = stt_result["duration"]
        logger.info("Pipeline [1/3] STT done: '%s…' (lang=%s)", transcript[:50], detected_lang)

        # ── Step 2: Text → Translated Text ────────────────────────────────
        logger.info("Pipeline [2/3] Translation starting…")
        translation_result = await TranslationService.translate(
            text=transcript,
            target_language=target_language,
            source_language=None if source_language == "auto" else source_language,
            provider=translation_provider,
        )
        translated_text   = translation_result["translated_text"]
        used_provider     = translation_result["provider"]
        logger.info("Pipeline [2/3] Translation done: '%s…'", translated_text[:50])

        # ── Step 3: Translated Text → Speech ──────────────────────────────
        logger.info("Pipeline [3/3] TTS starting…")
        audio_out = await TTSService.synthesize(
            text=translated_text,
            language=target_language,
            slow=slow_speech,
            provider=tts_provider,
        )

        # Save output audio to a temp file so it can be downloaded
        file_id  = uuid.uuid4().hex
        out_path = OUTPUT_DIR / f"{file_id}.mp3"
        out_path.write_bytes(audio_out)
        logger.info("Pipeline [3/3] TTS done, saved to %s", out_path)

        return {
            "original_transcript":   transcript,
            "translated_text":       translated_text,
            "source_language":       detected_lang,
            "target_language":       target_language,
            "translation_provider":  used_provider,
            "audio_url":             f"{BASE_URL}/api/v1/audio/download/{file_id}.mp3",
            "duration":              duration,
        }

    @staticmethod
    def get_output_path(filename: str) -> Path | None:
        """Resolve a download filename to its full path safely."""
        # Sanitise — only allow simple filenames, no path traversal
        safe_name = Path(filename).name
        path = OUTPUT_DIR / safe_name
        return path if path.exists() else None