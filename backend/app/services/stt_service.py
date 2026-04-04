# backend/app/services/stt_service.py
"""
Speech-to-Text Service
-----------------------
Uses OpenAI Whisper running LOCALLY — completely free, no API key needed.

Install: pip install openai-whisper
         pip install ffmpeg-python   (Whisper needs ffmpeg on PATH)

Windows ffmpeg install:
  winget install ffmpeg
  or download from https://ffmpeg.org/download.html and add to PATH
"""

from __future__ import annotations

import io
import logging
import tempfile
import os
import asyncio
from pathlib import Path

from app.config.settings import settings

logger = logging.getLogger(__name__)

# Supported audio MIME types
SUPPORTED_MIME_TYPES = {
    "audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav",
    "audio/ogg", "audio/webm", "audio/mp4", "audio/m4a",
    "audio/flac", "audio/x-flac", "video/mp4", "video/webm",
}

SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".ogg", ".webm", ".mp4", ".m4a", ".flac"}


class STTService:
    """
    Wraps OpenAI Whisper for local speech-to-text transcription.
    The model is loaded once and cached for subsequent requests.
    """

    _model = None   # lazy-loaded singleton

    @classmethod
    def load_model(cls):
        """Load Whisper model into memory (called once at startup or first use)."""
        if cls._model is not None:
            return cls._model

        try:
            import whisper  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "openai-whisper is not installed. "
                "Run: pip install openai-whisper"
            ) from exc

        model_size = settings.WHISPER_MODEL_SIZE
        logger.info("Loading Whisper model '%s'…", model_size)
        cls._model = whisper.load_model(model_size)
        logger.info("Whisper model '%s' loaded successfully.", model_size)
        return cls._model

    @classmethod
    async def transcribe_bytes(
        cls,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        language: str | None = None,
    ) -> dict:
        """
        Transcribe raw audio bytes.

        Args:
            audio_bytes : Raw audio file content
            filename    : Original filename (used to infer extension)
            language    : Optional ISO-639-1 language hint (e.g. 'en', 'es')
                          Pass None for auto-detection.

        Returns dict with keys:
            transcript, language, duration, model
        """
        # Validate extension
        ext = Path(filename).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported audio format '{ext}'. "
                f"Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
            )

        # Whisper is synchronous — run in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: cls._transcribe_sync(audio_bytes, ext, language),
        )
        return result

    @classmethod
    def _transcribe_sync(
        cls,
        audio_bytes: bytes,
        ext: str,
        language: str | None,
    ) -> dict:
        """Synchronous transcription — runs inside a thread pool executor."""
        model = cls.load_model()

        # Sniff actual format from magic bytes
        # webm starts with 0x1A 0x45 0xDF 0xA3
        # ogg starts with OggS
        if audio_bytes[:4] == b'\x1a\x45\xdf\xa3':
            ext = ".webm"
        elif audio_bytes[:4] == b'OggS':
            ext = ".ogg"

        # Write to a temp file (Whisper needs a file path, not bytes)
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            options: dict = {"fp16": False}   # fp16=False for CPU compatibility
            if language:
                options["language"] = language

            result = model.transcribe(tmp_path, **options)

            return {
                "transcript": result["text"].strip(),
                "language":   result.get("language", language or "unknown"),
                "duration":   cls._get_duration(result),
                "model":      settings.WHISPER_MODEL_SIZE,
            }
        finally:
            os.unlink(tmp_path)   # always clean up temp file

    @staticmethod
    def _get_duration(whisper_result: dict) -> float:
        """Extract audio duration from Whisper segments."""
        segments = whisper_result.get("segments", [])
        if segments:
            return round(segments[-1].get("end", 0.0), 2)
        return 0.0
