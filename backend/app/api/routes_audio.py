# backend/app/api/routes_audio.py
"""
Audio Routes
------------
POST /api/v1/audio/transcribe   – audio file → transcript
POST /api/v1/audio/synthesize   – text → MP3 stream
POST /api/v1/audio/pipeline     – audio → transcribe → translate → MP3 stream
GET  /api/v1/audio/status       – health check
"""

import io
import json
import logging
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from app.models.audio_models        import TranscriptionResponse, SynthesisRequest
from app.services.stt_service       import STTService, SUPPORTED_EXTENSIONS
from app.services.tts_service       import TTSService
from app.services.pipeline_services  import PipelineServices

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_UPLOAD_MB    = 25
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024


# ── GET /status ──────────────────────────────────────────────────────────────

@router.get("/status")
async def audio_status():
    return {
        "stt":      "Google Speech Recognition (free)",
        "tts":      "gTTS (free)",
        "pipeline": "STT → Translate → TTS",
    }


# ── POST /transcribe ─────────────────────────────────────────────────────────

@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Transcribe an audio file to text",
)
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str    = Form(default=""),
):
    audio_bytes = await file.read()
    if len(audio_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(400, detail=f"File too large. Max is {MAX_UPLOAD_MB} MB.")

    ext = Path(file.filename or "audio.wav").suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(400, detail=f"Unsupported format '{ext}'.")

    try:
        result = await STTService.transcribe_bytes(
            audio_bytes=audio_bytes,
            filename=file.filename or "audio.wav",
            language=language.strip() or None,
        )
    except RuntimeError as exc:
        raise HTTPException(503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc))
    except Exception:
        logger.exception("Unexpected STT error")
        raise HTTPException(500, detail="Transcription failed unexpectedly.")

    return TranscriptionResponse(**result)


# ── POST /synthesize ─────────────────────────────────────────────────────────

@router.post(
    "/synthesize",
    status_code=status.HTTP_200_OK,
    summary="Convert text to speech — returns MP3 audio stream",
)
async def synthesize_speech(request: SynthesisRequest):
    try:
        audio_bytes = await TTSService.synthesize(
            text=request.text,
            language=request.language,
            slow=request.slow,
        )
    except RuntimeError as exc:
        raise HTTPException(503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc))
    except Exception:
        logger.exception("Unexpected TTS error")
        raise HTTPException(500, detail="Speech synthesis failed unexpectedly.")

    return StreamingResponse(
        io.BytesIO(audio_bytes),
        media_type="audio/mpeg",
        headers={"Content-Disposition": "attachment; filename=speech.mp3"},
    )


# ── POST /pipeline ───────────────────────────────────────────────────────────

@router.post(
    "/pipeline",
    status_code=status.HTTP_200_OK,
    summary="Full pipeline: audio in → transcribe → translate → audio out",
)
async def audio_pipeline(
    file: UploadFile          = File(...),
    target_language: str      = Form(...),
    source_language: str      = Form(default="auto"),
    translation_provider: str = Form(default=""),
    slow_speech: bool         = Form(default=False),
):
    """
    Runs the full pipeline and returns a multipart-like JSON response
    with text results + base64 audio so it works on ephemeral filesystems.
    """
    audio_bytes = await file.read()
    if len(audio_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(400, detail=f"File too large. Max is {MAX_UPLOAD_MB} MB.")

    try:
        result = await PipelineServices.run(
            audio_bytes=audio_bytes,
            filename=file.filename or "audio.wav",
            target_language=target_language,
            source_language=source_language,
            translation_provider=translation_provider or None,
            slow_speech=slow_speech,
        )
    except RuntimeError as exc:
        raise HTTPException(503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc))
    except Exception:
        logger.exception("Unexpected pipeline error")
        raise HTTPException(500, detail="Pipeline failed unexpectedly.")

    # Convert audio bytes to base64 so frontend can play it directly
    import base64
    audio_b64 = base64.b64encode(result["audio_bytes"]).decode("utf-8")

    return {
        "original_transcript":  result["original_transcript"],
        "translated_text":      result["translated_text"],
        "source_language":      result["source_language"],
        "target_language":      result["target_language"],
        "translation_provider": result["translation_provider"],
        "duration":             result["duration"],
        "audio_b64":            audio_b64,   # base64 MP3 — no file download needed
    }