# backend/app/api/routes_stream.py
"""
WebSocket Streaming Routes
---------------------------
WS  /api/v1/stream/stt           – live audio → real-time transcript
WS  /api/v1/stream/translate     – live audio → transcript + translation
WS  /api/v1/stream/pipeline      – live audio → transcript + translation + speech
GET /api/v1/stream/status        – health check
"""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.services.stream_service import manager, StreamSession

logger = logging.getLogger(__name__)
router = APIRouter()


# ── GET /status ──────────────────────────────────────────────────────────────

@router.get("/status")
async def stream_status():
    return {
        "active_connections": len(manager.active),
        "endpoints": {
            "stt":      "ws://localhost:8000/api/v1/stream/stt",
            "translate": "ws://localhost:8000/api/v1/stream/translate",
            "pipeline": "ws://localhost:8000/api/v1/stream/pipeline",
        },
    }


# ── WS /stt ──────────────────────────────────────────────────────────────────

@router.websocket("/stt")
async def websocket_stt(
    websocket: WebSocket,
    language: str = Query(default="auto", description="Source language code or 'auto'"),
):
    """
    Real-time Speech-to-Text via WebSocket.

    HOW TO USE:
      1. Connect: ws://localhost:8000/api/v1/stream/stt?language=en
      2. Send raw audio bytes continuously (WAV chunks preferred)
      3. Receive JSON transcripts:
         {"type": "transcript", "text": "...", "language": "en", "is_final": false}
      4. Send {"action": "stop"} to end session cleanly

    EXAMPLE (JavaScript):
      const ws = new WebSocket('ws://localhost:8000/api/v1/stream/stt?language=en');
      ws.onmessage = (event) => console.log(JSON.parse(event.data));

      navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
        const recorder = new MediaRecorder(stream);
        recorder.ondataavailable = (e) => ws.send(e.data);
        recorder.start(1000);  // send chunk every 1 second
      });
    """
    await manager.connect(websocket)
    try:
        session = StreamSession(
            ws=websocket,
            source_language=language,
            translate=False,
            speak=False,
        )
        await session.run()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)


# ── WS /translate ─────────────────────────────────────────────────────────────

@router.websocket("/translate")
async def websocket_translate(
    websocket: WebSocket,
    source_language: str = Query(default="auto",  description="Source language or 'auto'"),
    target_language: str = Query(default="es",    description="Target language code"),
    provider: str        = Query(default="",      description="Translation provider override"),
):
    """
    Real-time Speech-to-Text + Translation via WebSocket.

    HOW TO USE:
      1. Connect: ws://localhost:8000/api/v1/stream/translate?target_language=es
      2. Send raw audio bytes
      3. Receive two JSON messages per chunk:
         {"type": "transcript", "text": "Hello",        "language": "en"}
         {"type": "translation","text": "Hola",          "source": "en", "target": "es"}
      4. Send {"action": "stop"} to end

    EXAMPLE (JavaScript):
      const ws = new WebSocket(
        'ws://localhost:8000/api/v1/stream/translate?source_language=en&target_language=es'
      );
    """
    await manager.connect(websocket)
    try:
        session = StreamSession(
            ws=websocket,
            source_language=source_language,
            target_language=target_language,
            translate=True,
            speak=False,
            translation_provider=provider or None,
        )
        await session.run()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)


# ── WS /pipeline ──────────────────────────────────────────────────────────────

@router.websocket("/pipeline")
async def websocket_pipeline(
    websocket: WebSocket,
    source_language: str = Query(default="auto", description="Source language or 'auto'"),
    target_language: str = Query(default="es",   description="Target language code"),
    provider: str        = Query(default="",     description="Translation provider override"),
    speak: bool          = Query(default=True,   description="Return synthesised audio"),
):
    """
    Full real-time pipeline via WebSocket:
    Audio in → Transcript → Translation → Speech out

    HOW TO USE:
      1. Connect: ws://localhost:8000/api/v1/stream/pipeline?target_language=es&speak=true
      2. Send raw audio bytes from microphone
      3. Receive three messages per chunk:
         {"type": "transcript", "text": "Hello",  "language": "en"}
         {"type": "translation","text": "Hola",   "source": "en", "target": "es"}
         <binary MP3 bytes>   ← play this audio directly
      4. Send {"action": "stop"} to end session cleanly

    EXAMPLE (JavaScript):
      const ws = new WebSocket(
        'ws://localhost:8000/api/v1/stream/pipeline?target_language=es&speak=true'
      );
      ws.onmessage = async (event) => {
        if (event.data instanceof Blob) {
          // Binary = audio — play it
          const url = URL.createObjectURL(event.data);
          new Audio(url).play();
        } else {
          // JSON = transcript or translation
          console.log(JSON.parse(event.data));
        }
      };
    """
    await manager.connect(websocket)
    try:
        session = StreamSession(
            ws=websocket,
            source_language=source_language,
            target_language=target_language,
            translate=True,
            speak=speak,
            translation_provider=provider or None,
        )
        await session.run()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)