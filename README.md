# VoxBridge 
### Multilingual Speech Translation System

A production-ready full-stack application that translates speech across 100+ languages in real time. Upload audio, speak live, or type text — VoxBridge transcribes, translates, and speaks back in your target language.

 **Live Demo:** [vox-bridge-nu.vercel.app](https://vox-bridge-nu.vercel.app)

 **Backend API:** [voxbridge-rcb9.onrender.com](https://voxbridge-rcb9.onrender.com/docs)

---

## Features

| Mode | Description | Endpoint |
|---|---|---|
| Text → Text | Translate text between 100+ languages | `POST /api/v1/text/translate` |
| Audio → Text | Transcribe audio files using Google STT | `POST /api/v1/audio/transcribe` |
| Text → Audio | Convert text to natural speech via gTTS | `POST /api/v1/audio/synthesize` |
| Audio → Audio | Full pipeline — speak in one language, hear another | `POST /api/v1/audio/pipeline` |
| Live Stream | Real-time mic → transcript → translation via WebSocket | `WS /api/v1/stream/pipeline` |

---

## Tech Stack

### Backend
| Technology | Purpose |
|---|---|
| **FastAPI** | REST API + WebSocket server |
| **SpeechRecognition** | Free Speech-to-Text (Google STT) |
| **deep-translator** | Free text translation (Google Translate) |
| **LibreTranslate** | Fallback translation provider |
| **gTTS** | Free Text-to-Speech |
| **Pydantic** | Request/response validation |
| **Uvicorn** | ASGI server |

### Frontend
| Technology | Purpose |
|---|---|
| **React 18** | UI framework |
| **Vite** | Build tool |
| **WebSocket API** | Real-time streaming |
| **MediaRecorder API** | Browser microphone capture |

### Deployment
| Service | Purpose |
|---|---|
| **Render** | Backend hosting (free tier) |
| **Vercel** | Frontend hosting (free tier) |

---

## Architecture

```

 React Frontend 
 TextTranslation AudioTranscribe TTS 
 LiveStream AudioPipeline 

 HTTP / WebSocket

 FastAPI Backend 

 routes_text routes_audio routes_stream 

 TranslationService STTService 
 TTSService PipelineService 
 StreamService 

```

### Design Patterns Used
- **Factory Pattern** — `TranslationService.get_provider()` creates provider instances
- **Singleton Pattern** — providers cached after first instantiation
- **Facade Pattern** — routes never call provider SDKs directly
- **Strategy Pattern** — swap translation provider via `.env` config
- **Abstract Base Class** — `BaseTranslator` enforces interface on all providers

---

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- ffmpeg ([download](https://ffmpeg.org/download.html))

### Backend Setup

```bash
# 1. Clone the repo
git clone https://github.com/yourusername/VoxBridge.git
cd VoxBridge/backend

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate # Windows
# source venv/bin/activate # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
cp .env.example .env

# 5. Run the server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd VoxBridge/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Open **http://localhost:3000** in your browser.

---

## Environment Variables

### Backend (.env)
```env
DEBUG=false
TRANSLATION_PROVIDER=auto
LIBRE_TRANSLATE_URL=https://libretranslate.com/translate
TTS_PROVIDER=gtts
AWS_REGION=us-east-1
```

### Frontend (.env)
```env
VITE_API_URL=http://127.0.0.1:8000
```

---

## API Reference

### Text Translation
```bash
POST /api/v1/text/translate
Content-Type: application/json

{
 "text": "Hello, how are you?",
 "source_language": "en",
 "target_language": "es"
}

# Response
{
 "original_text": "Hello, how are you?",
 "translated_text": "Hola, ¿cómo estás?",
 "source_language": "en",
 "target_language": "es",
 "provider": "auto",
 "character_count": 19
}
```

### Transcribe Audio
```bash
POST /api/v1/audio/transcribe
Content-Type: multipart/form-data

file: <audio file>
language: en # optional

# Response
{
 "transcript": "Hello, how are you?",
 "language": "en",
 "duration": 2.4,
 "model": "google-speech-recognition"
}
```

### Text to Speech
```bash
POST /api/v1/audio/synthesize
Content-Type: application/json

{
 "text": "Hola, ¿cómo estás?",
 "language": "es",
 "slow": false
}

# Response: MP3 audio stream
```

### Full Pipeline
```bash
POST /api/v1/audio/pipeline
Content-Type: multipart/form-data

file: <audio file>
target_language: es
source_language: auto

# Response
{
 "original_transcript": "Hello, how are you?",
 "translated_text": "Hola, ¿cómo estás?",
 "source_language": "en",
 "target_language": "es",
 "translation_provider": "auto",
 "duration": 2.4,
 "audio_b64": "<base64 encoded MP3>"
}
```

### WebSocket Streaming
```javascript
// Connect
const ws = new WebSocket(
 'ws://localhost:8000/api/v1/stream/pipeline?source_language=en&target_language=es'
)

// Send audio chunks
ws.send(audioBlob)

// Receive messages
// {"type": "transcript", "text": "Hello", "language": "en"}
// {"type": "translation", "text": "Hola", "source": "en", "target": "es"}
// <binary MP3 bytes>
```

---

## Project Structure

```
VoxBridge/
 backend/
 app/
 main.py # App factory, CORS, routing
 config/
 settings.py # Centralised config
 models/
 text_models.py # Text translation schemas
 audio_models.py # Audio endpoint schemas
 services/
 translation_service.py # Translation (deep-translator + LibreTranslate)
 stt_service.py # Speech-to-Text (Google STT)
 tts_service.py # Text-to-Speech (gTTS)
 pipeline_services.py # Full audio-to-audio pipeline
 stream_service.py # WebSocket streaming
 api/
 routes_text.py # Text translation endpoints
 routes_audio.py # Audio endpoints
 routes_stream.py # WebSocket endpoints
 requirements.txt
 .env.example

 frontend/
 src/
 App.jsx # Main app + navigation
 App.css # Global styles
 api.js # Backend API calls
 components/
 TextTranslation.jsx # Text → Text UI
 AudioTranscribe.jsx # Audio → Text UI
 TextToSpeech.jsx # Text → Audio UI
 LiveStream.jsx # Real-time streaming UI
 AudioPipeline.jsx # Full pipeline UI
 package.json
 vite.config.js
```

---

## Deployment

### Backend → Render
1. Push to GitHub
2. Create new Web Service on [render.com](https://render.com)
3. Set **Root Directory** to `backend`
4. Set **Start Command** to `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables

### Frontend → Vercel
1. Import repo on [vercel.com](https://vercel.com)
2. Set **Root Directory** to `frontend`
3. Add environment variable: `VITE_API_URL=https://your-backend.onrender.com`
4. Deploy

---

## Free Tier Limits

| Service | Limit |
|---|---|
| Google STT (SpeechRecognition) | 60 min/day |
| deep-translator | Unlimited (unofficial) |
| LibreTranslate | Unlimited (public instance) |
| gTTS | Unlimited |
| Render free tier | 512MB RAM, sleeps after 15min inactivity |
| Vercel free tier | 100GB bandwidth/month |

---

## License

MIT License — free to use, modify and distribute.

---

## ‍ Author

Built by **Srihitha** as a full-stack ML integration project demonstrating:
- Production REST API design with FastAPI
- Real-time WebSocket streaming
- Provider-agnostic service architecture
- Free-tier cloud deployment
