// frontend/src/api.js
const BASE = import.meta.env.VITE_API_URL 
  ? `${import.meta.env.VITE_API_URL}/api/v1`
  : "http://127.0.0.1:8000/api/v1"

const WS_BASE = import.meta.env.VITE_API_URL
  ? import.meta.env.VITE_API_URL.replace("https://", "wss://").replace("http://", "ws://")
  : "ws://127.0.0.1:8000"

export const LANGUAGES = {
  "auto": "Auto detect",
  "en": "English", "es": "Spanish", "fr": "French",
  "de": "German",  "it": "Italian", "pt": "Portuguese",
  "hi": "Hindi",   "te": "Telugu",  "ta": "Tamil",
  "ar": "Arabic",  "zh": "Chinese", "ja": "Japanese",
  "ko": "Korean",  "ru": "Russian", "nl": "Dutch",
  "sv": "Swedish", "pl": "Polish",  "tr": "Turkish",
  "uk": "Ukrainian","vi": "Vietnamese", "id": "Indonesian",
}

export const LANG_OPTIONS = Object.entries(LANGUAGES).map(([code, name]) => ({
  code, name
}))

// ── Text translation ──────────────────────────────────────────────────────────
export async function translateText({ text, source_language, target_language }) {
  const res = await fetch(`${BASE}/text/translate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, source_language, target_language }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || "Translation failed")
  }
  return res.json()
}

// ── STT: transcribe audio file ────────────────────────────────────────────────
export async function transcribeAudio({ file, language }) {
  const form = new FormData()
  form.append("file", file)
  form.append("language", language || "")
  const res = await fetch(`${BASE}/audio/transcribe`, { method: "POST", body: form })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || "Transcription failed")
  }
  return res.json()
}

// ── TTS: synthesise speech ────────────────────────────────────────────────────
export async function synthesiseSpeech({ text, language, slow = false }) {
  const res = await fetch(`${BASE}/audio/synthesize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, language, slow }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || "Synthesis failed")
  }
  // Returns audio blob
  return res.blob()
}

// ── Pipeline: audio file → translated audio ───────────────────────────────────
export async function runPipeline({ file, target_language, source_language = "auto" }) {
  const form = new FormData()
  form.append("file", file)
  form.append("target_language", target_language)
  form.append("source_language", source_language)
  const res = await fetch(`${BASE}/audio/pipeline`, { method: "POST", body: form })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || "Pipeline failed")
  }
  return res.json()
}

// ── WebSocket factory ─────────────────────────────────────────────────────────
export function createStreamWS({ endpoint, source_language, target_language, speak = true }) {
  const params = new URLSearchParams({ source_language, target_language, speak: String(speak) })
  return new WebSocket(`${WS_BASE}/api/v1/stream/${endpoint}?${params}`)
}