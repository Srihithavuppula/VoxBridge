# backend/app/services/stream_service.py
"""
WebSocket Stream Service
-------------------------
Manages real-time audio streaming connections.

How it works:
  1. Client connects via WebSocket
  2. Client sends raw audio chunks (bytes) continuously
  3. Server buffers chunks until enough audio is accumulated
  4. Server runs Whisper on the buffer → sends back transcript
  5. Optionally translates transcript → sends back translation
  6. Optionally synthesises translation → sends back audio bytes

Message protocol (server → client):
  All messages are JSON except audio response which is raw bytes.

  {"type": "transcript", "text": "...", "language": "en", "is_final": false}
  {"type": "translation", "text": "...", "source": "en", "target": "es"}
  {"type": "error",       "message": "..."}
  {"type": "status",      "message": "..."}
  bytes  → synthesised audio chunk (MP3)
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import tempfile
import os
from pathlib import Path
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

from app.services.stt_service         import STTService
from app.services.translation_service import TranslationService
from app.services.tts_service         import TTSService
from app.config.settings              import settings

logger = logging.getLogger(__name__)

# Minimum bytes before we attempt transcription (~1 second of audio)
MIN_CHUNK_BYTES = 16_000
# Maximum buffer size before forced transcription (~10 seconds)
MAX_BUFFER_BYTES = 160_000


class ConnectionManager:
    """Tracks all active WebSocket connections."""

    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)
        logger.info("WebSocket connected. Total active: %d", len(self.active))

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)
        logger.info("WebSocket disconnected. Total active: %d", len(self.active))

    async def send_json(self, ws: WebSocket, data: dict):
        try:
            await ws.send_json(data)
        except Exception as exc:
            logger.warning("Failed to send JSON: %s", exc)

    async def send_bytes(self, ws: WebSocket, data: bytes):
        try:
            await ws.send_bytes(data)
        except Exception as exc:
            logger.warning("Failed to send bytes: %s", exc)


# Global connection manager instance
manager = ConnectionManager()


class StreamSession:
    """
    Handles one WebSocket streaming session.
    Buffers incoming audio, transcribes, translates, and speaks.
    """

    def __init__(
        self,
        ws: WebSocket,
        source_language: str = "auto",
        target_language: Optional[str] = None,
        translate: bool = False,
        speak: bool = False,
        translation_provider: Optional[str] = None,
    ):
        self.ws                   = ws
        self.source_language      = source_language
        self.target_language      = target_language
        self.translate            = translate and target_language is not None
        self.speak                = speak and self.translate
        self.translation_provider = translation_provider
        self.buffer               = bytearray()
        self.is_running           = True

    async def send_status(self, message: str):
        await manager.send_json(self.ws, {"type": "status", "message": message})

    async def send_error(self, message: str):
        await manager.send_json(self.ws, {"type": "error", "message": message})

    async def process_buffer(self, is_final: bool = False):
        """Transcribe current buffer and optionally translate + speak."""
        if len(self.buffer) < MIN_CHUNK_BYTES and not is_final:
            return  # not enough audio yet

        audio_bytes = bytes(self.buffer)
        self.buffer.clear()

        # ── STT ─────────────────────────────────────────────────────────
        try:
            stt_result = await STTService.transcribe_bytes(
                audio_bytes=audio_bytes,
                filename="stream_chunk.webm",  # browser MediaRecorder sends webm
                language=None if self.source_language == "auto" else self.source_language,
            )
        except Exception as exc:
            await self.send_error(f"Transcription failed: {exc}")
            return

        transcript = stt_result["transcript"]
        detected   = stt_result["language"]

        if not transcript.strip():
            return  # empty result — skip

        # Send transcript to client
        await manager.send_json(self.ws, {
            "type":     "transcript",
            "text":     transcript,
            "language": detected,
            "is_final": is_final,
        })

        if not self.translate:
            return

        # ── Translation ──────────────────────────────────────────────────
        try:
            trans_result = await TranslationService.translate(
                text=transcript,
                target_language=self.target_language,
                source_language=detected,
                provider=self.translation_provider,
            )
        except Exception as exc:
            await self.send_error(f"Translation failed: {exc}")
            return

        translated = trans_result["translated_text"]

        await manager.send_json(self.ws, {
            "type":   "translation",
            "text":   translated,
            "source": detected,
            "target": self.target_language,
        })

        if not self.speak:
            return

        # ── TTS ──────────────────────────────────────────────────────────
        try:
            audio_out = await TTSService.synthesize(
                text=translated,
                language=self.target_language,
            )
            await manager.send_bytes(self.ws, audio_out)
        except Exception as exc:
            await self.send_error(f"TTS failed: {exc}")

    async def run(self):
        """Main loop — receive audio chunks from client and process them."""
        await self.send_status("Connected. Send audio chunks as binary frames.")

        try:
            while self.is_running:
                try:
                    # Receive next message (binary audio chunk or text command)
                    message = await asyncio.wait_for(
                        self.ws.receive(),
                        timeout=30.0,   # 30s idle timeout
                    )
                except asyncio.TimeoutError:
                    await self.send_status("Idle timeout. Send audio to continue.")
                    continue

                # ── Text command ─────────────────────────────────────────
                if "text" in message:
                    try:
                        cmd = json.loads(message["text"])
                        if cmd.get("action") == "stop":
                            # Process remaining buffer before closing
                            if self.buffer:
                                await self.process_buffer(is_final=True)
                            await self.send_status("Session ended.")
                            break
                        elif cmd.get("action") == "flush":
                            await self.process_buffer(is_final=True)
                    except json.JSONDecodeError:
                        pass

                # ── Binary audio chunk ───────────────────────────────────
                elif "bytes" in message and message["bytes"]:
                    self.buffer.extend(message["bytes"])

                    # Process when buffer is large enough
                    if len(self.buffer) >= MAX_BUFFER_BYTES:
                        await self.process_buffer(is_final=False)

        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected during session.")
        except Exception as exc:
            logger.exception("Unexpected stream session error: %s", exc)
            await self.send_error(f"Session error: {exc}")
        finally:
            # Process any remaining audio
            if self.buffer:
                await self.process_buffer(is_final=True)
            self.is_running = False