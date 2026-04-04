# backend/app/main.py
"""
Multilingual Speech Translation System
FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from pathlib import Path

from app.api import routes_text, routes_audio, routes_stream
from app.config.settings import settings


# ---------------------------------------------------------------------------
# Lifespan: startup / shutdown logic
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[startup] {settings.APP_NAME} v{settings.APP_VERSION} is starting…")
    # Pre-load Whisper model so first request is fast
    try:
        from app.services.stt_service import STTService
        STTService.load_model()
    except Exception as e:
        print(f"[startup] Whisper model load skipped: {e}")
    yield
    print("[shutdown] Cleaning up resources…")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "End-to-end multilingual speech translation system supporting "
            "Speech-to-Text, Text-to-Text, Text-to-Speech, and full pipelines "
            "with real-time WebSocket streaming."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # -- CORS ---------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -- Routers ------------------------------------------------------------
    app.include_router(routes_text.router,   prefix="/api/v1/text",   tags=["Text Translation"])
    app.include_router(routes_audio.router,  prefix="/api/v1/audio",  tags=["Audio / STT / TTS"])
    app.include_router(routes_stream.router, prefix="/api/v1/stream", tags=["Streaming (WebSocket)"])

    # -- Static files (stream test page) ------------------------------------
    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # -- Routes -------------------------------------------------------------
    @app.get("/", tags=["Root"])
    async def root():
        return {
            "app":      settings.APP_NAME,
            "version":  settings.APP_VERSION,
            "docs":     "/docs",
            "health":   "/health",
            "stream_test": "/static/stream_test.html",
        }

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {
            "status":  "ok",
            "app":     settings.APP_NAME,
            "version": settings.APP_VERSION,
        }

    @app.get("/stream-test", tags=["Dev Tools"])
    async def stream_test_page():
        """Open the browser-based WebSocket test UI."""
        return FileResponse(str(static_dir / "stream_test.html"))

    return app


app = create_app()