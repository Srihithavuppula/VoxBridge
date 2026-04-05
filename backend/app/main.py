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


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[startup] {settings.APP_NAME} v{settings.APP_VERSION} starting…")
    print(f"[startup] STT: SpeechRecognition | Translation: {settings.TRANSLATION_PROVIDER} | TTS: {settings.TTS_PROVIDER}")
    yield
    print("[shutdown] Cleaning up…")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Multilingual speech translation — STT, TTS, translation, real-time streaming.",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(routes_text.router,   prefix="/api/v1/text",   tags=["Text Translation"])
    app.include_router(routes_audio.router,  prefix="/api/v1/audio",  tags=["Audio / STT / TTS"])
    app.include_router(routes_stream.router, prefix="/api/v1/stream", tags=["Streaming (WebSocket)"])

    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", tags=["Root"])
    async def root():
        return {
            "app":         settings.APP_NAME,
            "version":     settings.APP_VERSION,
            "docs":        "/docs",
            "health":      "/health",
            "stream_test": "/stream-test",
        }

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}

    @app.get("/stream-test", tags=["Dev Tools"])
    async def stream_test_page():
        return FileResponse(str(static_dir / "stream_test.html"))

    return app


app = create_app()