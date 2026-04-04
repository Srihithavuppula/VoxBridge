# backend/app/models/audio_models.py
"""
Pydantic schemas for STT, TTS, and pipeline endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional


# ── STT ─────────────────────────────────────────────────────────────────────

class TranscriptionResponse(BaseModel):
    transcript: str
    language:   str        # detected language code
    duration:   float      # audio duration in seconds
    model:      str        # whisper model size used

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "transcript": "Hello, how are you?",
                "language":   "en",
                "duration":   2.4,
                "model":      "base",
            }]
        }
    }


# ── TTS ─────────────────────────────────────────────────────────────────────

class SynthesisRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=3000,
                      description="Text to convert to speech.")
    language: str = Field(default="en",
                          description="BCP-47 language code for the voice.")
    slow: bool = Field(default=False,
                       description="Speak slowly (gTTS only).")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "text":     "Hola, ¿cómo estás?",
                "language": "es",
                "slow":     False,
            }]
        }
    }


# ── Pipeline ─────────────────────────────────────────────────────────────────

class PipelineResponse(BaseModel):
    original_transcript: str
    translated_text:     str
    source_language:     str
    target_language:     str
    translation_provider: str
    audio_url:           str    # relative path to download the synthesised audio
    duration:            float  # original audio duration in seconds

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "original_transcript":  "Hello, how are you?",
                "translated_text":      "Hola, ¿cómo estás?",
                "source_language":      "en",
                "target_language":      "es",
                "translation_provider": "auto",
                "audio_url":            "/api/v1/audio/download/abc123.mp3",
                "duration":             2.4,
            }]
        }
    }