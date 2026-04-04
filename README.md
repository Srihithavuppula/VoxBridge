# Multilingual Speech Translation System — Backend

## Step 1 Deliverables

| File | Purpose |
|---|---|
| `app/main.py` | FastAPI app factory, CORS, router registration, health check |
| `app/config/settings.py` | Centralised config via `pydantic-settings` + `.env` |
| `app/models/text_models.py` | Pydantic request/response schemas for translation |
| `app/services/translation_service.py` | Provider-agnostic translation service (Google / OpenAI) |
| `app/api/routes_text.py` | `POST /translate` and `GET /languages` endpoints |
| `app/api/routes_audio.py` | Stub — implemented in Step 2 |
| `app/api/routes_stream.py` | Stub — implemented in Step 3 |

---

## Quick Start

```bash
# 1. Clone / copy the backend folder
cd backend

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY or OPENAI_API_KEY

# 5. Run the server
uvicorn app.main:app --reload --port 8000
```

Open **http://localhost:8000/docs** for the interactive Swagger UI.

---

## API Reference

### `POST /api/v1/text/translate`

**Request**
```json
{
  "text": "Hello, how are you?",
  "source_language": "en",
  "target_language": "es"
}
```

**Response**
```json
{
  "original_text": "Hello, how are you?",
  "translated_text": "Hola, ¿cómo estás?",
  "source_language": "en",
  "target_language": "es",
  "provider": "google",
  "character_count": 19
}
```

### `GET /api/v1/text/languages`
Returns all 100+ supported BCP-47 language codes.

### `GET /health`
```json
{ "status": "ok", "app": "Multilingual Speech Translation System", "version": "0.1.0" }
```

---

## Architecture

```
routes_text.py          ← thin HTTP layer (validation, HTTP errors)
      │
      ▼
TranslationService      ← orchestration, provider routing, logging
      │
      ├── GoogleTranslator   ← google-cloud-translate
      └── OpenAITranslator   ← GPT-4o chat completion
```

- **Routes** only speak HTTP — they never call provider SDKs directly.
- **Service** is provider-agnostic; swap backends by changing `TRANSLATION_PROVIDER` in `.env`.
- **Providers** are lazy-initialised singletons inside `TranslationService._providers`.

---

## Next Steps

| Step | Feature |
|---|---|
| Step 2 | STT (`/audio/transcribe`) via Whisper + TTS (`/audio/synthesize`) via gTTS/Polly |
| Step 3 | WebSocket streaming for real-time audio-to-text |
| Step 4 | Full audio-to-audio pipeline service |
| Step 5 | React frontend |