// frontend/src/components/AudioPipeline.jsx
import { useState, useRef } from "react"
import { runPipeline, LANG_OPTIONS } from "../api"

const BASE = "http://127.0.0.1:8000"

export default function AudioPipeline() {
  const [file, setFile] = useState(null)
  const [sourceLang, setSource] = useState("auto")
  const [targetLang, setTarget] = useState("es")
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [drag, setDrag] = useState(false)
  const [step, setStep] = useState(0) // 0=idle 1=stt 2=translate 3=tts
  const inputRef = useRef()
  const audioRef = useRef()

  function onFile(f) {
    if (!f) return
    setFile(f); setResult(null); setError(""); setStep(0)
  }

  async function handleRun() {
    if (!file) return
    setLoading(true); setError(""); setResult(null)

    // Simulate step progress
    setStep(1)
    const stepTimer1 = setTimeout(() => setStep(2), 3000)
    const stepTimer2 = setTimeout(() => setStep(3), 6000)

    try {
      const data = await runPipeline({
        file,
        target_language: targetLang,
        source_language: sourceLang,
      })
      clearTimeout(stepTimer1); clearTimeout(stepTimer2)
      setStep(0)
      setResult(data)
      setTimeout(() => audioRef.current?.play(), 300)
    } catch (e) {
      clearTimeout(stepTimer1); clearTimeout(stepTimer2)
      setStep(0)
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const steps = [
    { label: "Transcribe", desc: "Whisper STT" },
    { label: "Translate", desc: "googletrans" },
    { label: "Synthesise", desc: "gTTS TTS" },
  ]

  return (
    <div>
      <div className="section-header">
        <h2 className="section-title">Audio to Audio</h2>
        <p className="section-desc">Upload audio in any language — get translated audio back automatically</p>
      </div>

      <div className="card">
        {/* Language selectors */}
        <div className="row" style={{ marginBottom: "1rem" }}>
          <div className="field" style={{ marginBottom: 0 }}>
            <label className="field-label">Source Language</label>
            <select value={sourceLang} onChange={e => setSource(e.target.value)}>
              {LANG_OPTIONS.map(l => <option key={l.code} value={l.code}>{l.name}</option>)}
            </select>
          </div>
          <div style={{ flex: "0 0 auto", display: "flex", alignItems: "flex-end", paddingBottom: "2px" }}>
            <span style={{ fontSize: "1.2rem", color: "var(--text3)" }}>→</span>
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label className="field-label">Target Language</label>
            <select value={targetLang} onChange={e => setTarget(e.target.value)}>
              {LANG_OPTIONS.filter(l => l.code !== "auto").map(l => (
                <option key={l.code} value={l.code}>{l.name}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Upload */}
        <div
          className={`upload-area ${drag ? "drag" : ""}`}
          onClick={() => inputRef.current.click()}
          onDragOver={e => { e.preventDefault(); setDrag(true) }}
          onDragLeave={() => setDrag(false)}
          onDrop={e => { e.preventDefault(); setDrag(false); onFile(e.dataTransfer.files[0]) }}
        >
          <div className="upload-icon">{file ? "🎵" : "⬆"}</div>
          {file
            ? <p className="upload-text"><strong>{file.name}</strong><br />{(file.size / 1024).toFixed(1)} KB</p>
            : <p className="upload-text"><strong>Click to upload audio</strong> or drag and drop<br />mp3, wav, ogg, webm, flac — max 25MB</p>
          }
          <input
            ref={inputRef}
            type="file"
            accept=".mp3,.wav,.ogg,.webm,.flac,.m4a"
            style={{ display: "none" }}
            onChange={e => onFile(e.target.files[0])}
          />
        </div>

        {/* Run button */}
        <div style={{ marginTop: "1rem" }}>
          <button
            className="btn btn-primary btn-lg"
            onClick={handleRun}
            disabled={loading || !file}
            style={{ width: "100%" }}
          >
            {loading
              ? <><span className="spinner" /> Processing…</>
              : "▶ Run Pipeline"
            }
          </button>
        </div>

        {/* Step progress */}
        {loading && (
          <div style={{ marginTop: "1.25rem" }}>
            <div style={{ display: "flex", gap: "0", alignItems: "center" }}>
              {steps.map((s, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", flex: 1 }}>
                  <div style={{ textAlign: "center", flex: 1 }}>
                    <div style={{
                      width: 32, height: 32, borderRadius: "50%", margin: "0 auto 4px",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: "0.8rem", fontWeight: 600,
                      background: step > i ? "var(--green)" : step === i + 1 ? "var(--accent)" : "var(--bg3)",
                      color: step >= i + 1 ? "#fff" : "var(--text3)",
                      transition: "all 0.3s",
                    }}>
                      {step > i ? "✓" : i + 1}
                    </div>
                    <div style={{ fontSize: "0.75rem", fontWeight: 500, color: step === i + 1 ? "var(--accent)" : "var(--text2)" }}>{s.label}</div>
                    <div style={{ fontSize: "0.7rem", color: "var(--text3)" }}>{s.desc}</div>
                  </div>
                  {i < steps.length - 1 && (
                    <div style={{ height: 1, flex: "0 0 20px", background: step > i + 1 ? "var(--green)" : "var(--border)", transition: "all 0.3s" }} />
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {error && <div className="error-msg" style={{ marginTop: "1rem" }}>⚠ {error}</div>}
      </div>

      {/* Result */}
      {result && (
        <div className="card">
          <div className="row" style={{ marginBottom: "1rem" }}>
            <div>
              <label className="field-label">Original Transcript</label>
              <div className="result-box">{result.original_transcript}</div>
            </div>
            <div>
              <label className="field-label">Translation</label>
              <div className="result-box">{result.translated_text}</div>
            </div>
          </div>

          <label className="field-label">Translated Audio</label>
          <audio
            ref={audioRef}
            src={`${BASE}${result.audio_url}`}
            controls
          />

          <div className="meta-row">
            <span className="badge badge-green">{result.source_language} → {result.target_language}</span>
            <span className="badge badge-green">Provider: {result.translation_provider}</span>
            <span className="badge badge-green">Duration: {result.duration}s</span>
          </div>

          <div style={{ marginTop: "0.75rem" }}>
            <a
              href={`${BASE}${result.audio_url}`}
              download
              className="btn btn-ghost"
              style={{ textDecoration: "none" }}
            >
              ↓ Download Audio
            </a>
          </div>
        </div>
      )}
    </div>
  )
}