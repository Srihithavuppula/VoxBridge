# backend/app/services/stt_service.py
"""
Speech-to-Text Service
-----------------------
Uses SpeechRecognition library with Google Speech API — FREE, no API key needed.
Much lighter than Whisper — works on Render free tier (512MB RAM).

Install: pip install SpeechRecognition pydub
         pip install ffmpeg-python  (ffmpeg must be on PATH)
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from pathlib import Path

from app.config.settings import settings

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".ogg", ".webm", ".mp4", ".m4a", ".flac"}


class STTService:
    """
    Wraps SpeechRecognition (Google STT) for speech-to-text.
    No model loading — API call based, very low memory usage.
    """

    _model = None  # kept for compatibility — not used

    @classmethod
    def load_model(cls):
        """No-op — SpeechRecognition needs no model loading."""
        logger.info("STT provider: SpeechRecognition (Google) — no model to load.")
        return True

    @classmethod
    async def transcribe_bytes(
        cls,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        language: str | None = None,
    ) -> dict:
        """
        Transcribe raw audio bytes using Google Speech Recognition.

        Args:
            audio_bytes : Raw audio file content
            filename    : Original filename (used to infer extension)
            language    : Optional BCP-47 language hint (e.g. 'en-US', 'es-ES')

        Returns dict with keys:
            transcript, language, duration, model
        """
        ext = Path(filename).suffix.lower()

        # Sniff actual format from magic bytes
        if audio_bytes[:4] == b'\x1a\x45\xdf\xa3':
            ext = ".webm"
        elif audio_bytes[:4] == b'OggS':
            ext = ".ogg"
        elif audio_bytes[:3] == b'ID3' or audio_bytes[:2] == b'\xff\xfb':
            ext = ".mp3"

        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported audio format '{ext}'. "
                f"Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
            )

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
        """Synchronous transcription — runs inside thread pool."""
        try:
            import speech_recognition as sr  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "SpeechRecognition is not installed. "
                "Run: pip install SpeechRecognition"
            ) from exc

        recognizer = sr.Recognizer()

        # Write to temp file
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            # Convert non-WAV formats to WAV using pydub
            wav_path = tmp_path
            if ext != ".wav":
                wav_path = tmp_path.replace(ext, ".wav")
                _convert_to_wav(tmp_path, wav_path)

            with sr.AudioFile(wav_path) as source:
                audio = recognizer.record(source)
                duration = source.DURATION or 0.0

            # Google Speech Recognition — free, no key needed
            lang_code = _to_bcp47(language) if language else "en-US"
            transcript = recognizer.recognize_google(audio, language=lang_code)

            return {
                "transcript": transcript.strip(),
                "language":   language or "en",
                "duration":   round(duration, 2),
                "model":      "google-speech-recognition",
            }

        except sr.UnknownValueError:
            return {
                "transcript": "",
                "language":   language or "en",
                "duration":   0.0,
                "model":      "google-speech-recognition",
            }
        except sr.RequestError as exc:
            raise RuntimeError(
                f"Google Speech API error: {exc}. "
                "Check your internet connection."
            )
        finally:
            # Clean up temp files
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            if wav_path != tmp_path and os.path.exists(wav_path):
                os.unlink(wav_path)

    @staticmethod
    def _get_duration(result: dict) -> float:
        return result.get("duration", 0.0)


def _convert_to_wav(input_path: str, output_path: str):
    """Convert any audio format to WAV using pydub."""
    try:
        from pydub import AudioSegment  # type: ignore
        ext = Path(input_path).suffix.lstrip(".")
        audio = AudioSegment.from_file(input_path, format=ext)
        audio.export(output_path, format="wav")
    except ImportError as exc:
        raise RuntimeError(
            "pydub is not installed. Run: pip install pydub"
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"Audio conversion failed: {exc}")


def _to_bcp47(lang: str) -> str:
    """Convert simple language code to BCP-47 format for Google STT."""
    mapping = {
        "en": "en-US", "es": "es-ES", "fr": "fr-FR",
        "de": "de-DE", "it": "it-IT", "pt": "pt-BR",
        "hi": "hi-IN", "te": "te-IN", "ta": "ta-IN",
        "ar": "ar-SA", "zh": "zh-CN", "ja": "ja-JP",
        "ko": "ko-KR", "ru": "ru-RU", "nl": "nl-NL",
        "sv": "sv-SE", "pl": "pl-PL", "tr": "tr-TR",
        "uk": "uk-UA", "vi": "vi-VN", "id": "id-ID",
    }
    return mapping.get(lang, f"{lang}-{lang.upper()}")