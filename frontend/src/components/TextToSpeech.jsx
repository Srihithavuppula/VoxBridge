// frontend/src/components/TextToSpeech.jsx
import { useState, useRef } from "react"
import { synthesiseSpeech, LANG_OPTIONS } from "../api"

export default function TextToSpeech() {
  const [text, setText]       = useState("")
  const [lang, setLang]       = useState("en")
  const [slow, setSlow]       = useState(false)
  const [audioUrl, setUrl]    = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState("")
  const audioRef              = useRef()

  async function handleSynth() {
    if (!text.trim()) return
    setLoading(true); setError(""); setUrl(null)
    try {
      const blob = await synthesiseSpeech({ text: text.trim(), language: lang, slow })
      const url  = URL.createObjectURL(blob)
      setUrl(url)
      setTimeout(() => audioRef.current?.play(), 100)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  function handleDownload() {
    if (!audioUrl) return
    const a = document.createElement("a")
    a.href = audioUrl
    a.download = "speech.mp3"
    a.click()
  }

  return (
    <div>
      <div className="section-header">
        <h2 className="section-title">Text to Speech</h2>
        <p className="section-desc">Convert any text into natural-sounding audio using gTTS</p>
      </div>

      <div className="card">
        <div className="row" style={{ marginBottom: "1rem" }}>
          <div className="field" style={{ marginBottom: 0 }}>
            <label className="field-label">Language</label>
            <select value={lang} onChange={e => setLang(e.target.value)}>
              {LANG_OPTIONS.filter(l => l.code !== "auto").map(l => (
                <option key={l.code} value={l.code}>{l.name}</option>
              ))}
            </select>
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label className="field-label">Speed</label>
            <select value={slow} onChange={e => setSlow(e.target.value === "true")}>
              <option value="false">Normal</option>
              <option value="true">Slow</option>
            </select>
          </div>
        </div>

        <div className="field">
          <label className="field-label">Text</label>
          <textarea
            value={text}
            onChange={e => setText(e.target.value)}
            placeholder="Type text to convert to speech…"
            rows={5}
          />
        </div>

        <div className="row-center">
          <button
            className="btn btn-primary"
            onClick={handleSynth}
            disabled={loading || !text.trim()}
          >
            {loading ? <><span className="spinner" /> Generating…</> : "▶ Generate Speech"}
          </button>

          {audioUrl && (
            <button className="btn btn-ghost" onClick={handleDownload}>
              ↓ Download MP3
            </button>
          )}
        </div>
      </div>

      {/* Audio player */}
      {(audioUrl || error) && (
        <div className="card">
          {error
            ? <div className="error-msg">⚠ {error}</div>
            : <>
                <label className="field-label">Audio Output</label>
                <audio ref={audioRef} src={audioUrl} controls />
                <div className="meta-row">
                  <span className="badge badge-green">Language: {lang}</span>
                  <span className="badge badge-green">Format: MP3</span>
                  <span className="badge badge-green">Provider: gTTS</span>
                </div>
              </>
          }
        </div>
      )}
    </div>
  )
}