# backend/app/api/routes_audio.py
"""
Audio Routes
------------
POST /api/v1/audio/transcribe        – audio file → transcript (Whisper STT)
POST /api/v1/audio/synthesize        – text → MP3 audio (gTTS / Polly)
POST /api/v1/audio/pipeline          – audio → transcribe → translate → audio
GET  /api/v1/audio/download/{filename}   – download synthesised audio
GET  /api/v1/audio/status            – health check
"""

import io
import logging
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse

from app.models.audio_models import TranscriptionResponse, SynthesisRequest, PipelineResponse
from app.services.stt_service import STTService, SUPPORTED_EXTENSIONS
from app.services.tts_service import TTSService
from app.services.pipeline_services import PipelineService

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_UPLOAD_MB = 25
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

# ── GET /status ──────────────────────────────────────────────────────────────

@router.get("/status")
async def audio_status():
    # Debug: Return audio component status
    return {
        "stt": "Whisper (local, free)",
        "tts": "gTTS (free)",
        "pipeline": "STT → Translate → TTS",
    }

# ── POST /transcribe ─────────────────────────────────────────────────────────

@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Transcribe an audio file to text (Whisper STT)",
)
async def transcribe_audio(
    file: UploadFile = File(..., description="Audio file to transcribe"),
    language: str = Form(default="", description="Optional language hint e.g. 'en'. Leave blank for auto-detect."),
):
    """
    Upload an audio file and receive its transcript.
    Supported formats: mp3, wav, ogg, webm, mp4, m4a, flac

    Example curl:
        curl -X POST http://127.0.0.1:8000/api/v1/audio/transcribe
             -F "file=@speech.mp3" -F "language=en"
    """
    audio_bytes = await file.read()
    if len(audio_bytes) > MAX_UPLOAD_BYTES:
        logger.warning(f"File too large: {len(audio_bytes)} bytes (max: {MAX_UPLOAD_BYTES})")
        raise HTTPException(400, detail=f"File too large. Maximum is {MAX_UPLOAD_MB} MB.")

    ext = Path(file.filename or "audio.wav").suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        logger.error(f"Unsupported format: {ext}, filename={file.filename}")
        raise HTTPException(
            400,
            detail=f"Unsupported format '{ext}'. Supported: {', '.join(SUPPORTED_EXTENSIONS)}",
        )

    try:
        result = await STTService.transcribe_bytes(
            audio_bytes=audio_bytes,
            filename=file.filename or "audio.wav",
            language=language.strip() or None,
        )
    except RuntimeError as exc:
        logger.error(f"STT RuntimeError: {exc}")
        raise HTTPException(503, detail=str(exc))
    except ValueError as exc:
        logger.error(f"STT ValueError: {exc}")
        raise HTTPException(400, detail=str(exc))
    except Exception as exc:
        logger.exception(f"Unexpected STT error: {exc}")
        raise HTTPException(500, detail="Transcription failed unexpectedly.")

    return TranscriptionResponse(**result)

# ── POST /synthesize ─────────────────────────────────────────────────────────

@router.post(
    "/synthesize",
    status_code=status.HTTP_200_OK,
    summary="Convert text to speech — returns MP3 audio stream",
)
async def synthesize_speech(request: SynthesisRequest):
    """
    Convert text to an MP3 audio stream.

    Example curl:
        curl -X POST http://127.0.0.1:8000/api/v1/audio/synthesize
             -H "Content-Type: application/json"
             -d '{"text": "Hola, como estas?", "language": "es"}'
             --output speech.mp3
    """
    try:
        audio_bytes = await TTSService.synthesize(
            text=request.text,
            language=request.language,
            slow=request.slow,
        )
    except RuntimeError as exc:
        logger.error(f"TTS RuntimeError: {exc}")
        raise HTTPException(503, detail=str(exc))
    except ValueError as exc:
        logger.error(f"TTS ValueError: {exc}")
        raise HTTPException(400, detail=str(exc))
    except Exception as exc:
        logger.exception(f"Unexpected TTS error: {exc}")
        raise HTTPException(500, detail="Speech synthesis failed unexpectedly.")

    return StreamingResponse(
        io.BytesIO(audio_bytes),
        media_type="audio/mpeg",
        headers={"Content-Disposition": "attachment; filename=speech.mp3"},
    )

# ── POST /pipeline ───────────────────────────────────────────────────────────

@router.post(
    "/pipeline",
    response_model=PipelineResponse,
    status_code=status.HTTP_200_OK,
    summary="Full pipeline: audio in → transcribe → translate → audio out",
)
async def audio_pipeline(
    file: UploadFile = File(..., description="Source audio file"),
    target_language: str = Form(..., description="Target language code e.g. 'es', 'fr', 'hi'"),
    source_language: str = Form(default="auto", description="Source language code or 'auto'"),
    translation_provider: str = Form(default="", description="Translation provider override"),
    slow_speech: bool = Form(default=False, description="Slow TTS output"),
):
    """
    Runs the complete audio-to-audio pipeline in one request:
      1. Transcribes uploaded audio with Whisper
      2. Translates transcript to target_language
      3. Synthesises translation back to speech
      4. Returns metadata + download URL for output audio

    Example curl:
        curl -X POST http://127.0.0.1:8000/api/v1/audio/pipeline
             -F "file=@speech.mp3"
             -F "target_language=es"
             -F "source_language=en"
    """
    audio_bytes = await file.read()
    if len(audio_bytes) > MAX_UPLOAD_BYTES:
        logger.warning(f"Pipeline file too large: {len(audio_bytes)} bytes (max: {MAX_UPLOAD_BYTES})")
        raise HTTPException(400, detail=f"File too large. Maximum is {MAX_UPLOAD_MB} MB.")

    try:
        result = await PipelineService.run(
            audio_bytes=audio_bytes,
            filename=file.filename or "audio.wav",
            target_language=target_language,
            source_language=source_language,
            translation_provider=translation_provider or None,
            slow_speech=slow_speech,
        )
    except RuntimeError as exc:
        logger.error(f"Pipeline RuntimeError: {exc}")
        raise HTTPException(503, detail=str(exc))
    except ValueError as exc:
        logger.error(f"Pipeline ValueError: {exc}")
        raise HTTPException(400, detail=str(exc))
    except Exception as exc:
        logger.exception(f"Unexpected pipeline error: {exc}")
        raise HTTPException(500, detail="Pipeline failed unexpectedly.")

    return PipelineResponse(**result)

# ── GET /download/{filename} ─────────────────────────────────────────────────

@router.get(
    "/download/{filename}",
    summary="Download a synthesised audio file",
)
async def download_audio(filename: str):
    """Download a previously synthesised audio file by filename."""
    path = PipelineService.get_output_path(filename)
    if path is None:
        logger.error(f"Audio file '{filename}' not found or expired in download_audio")
        raise HTTPException(404, detail=f"Audio file '{filename}' not found or expired.")
    return FileResponse(path=str(path), media_type="audio/mpeg", filename=filename)