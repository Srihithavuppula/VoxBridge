// frontend/src/components/AudioPipeline.jsx
import { useState, useRef } from "react"
import { LANG_OPTIONS } from "../api"

const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"

export default function AudioPipeline() {
  const [file, setFile]         = useState(null)
  const [sourceLang, setSource] = useState("auto")
  const [targetLang, setTarget] = useState("es")
  const [result, setResult]     = useState(null)
  const [audioUrl, setAudioUrl] = useState(null)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState("")
  const [drag, setDrag]         = useState(false)
  const [step, setStep]         = useState(0)
  const inputRef                = useRef()
  const audioRef                = useRef()

  function onFile(f) {
    if (!f) return
    setFile(f); setResult(null); setError(""); setStep(0); setAudioUrl(null)
  }

  async function handleRun() {
    if (!file) return
    setLoading(true); setError(""); setResult(null); setAudioUrl(null)

    setStep(1)
    const t1 = setTimeout(() => setStep(2), 3000)
    const t2 = setTimeout(() => setStep(3), 6000)

    try {
      const form = new FormData()
      form.append("file", file)
      form.append("target_language", targetLang)
      form.append("source_language", sourceLang)

      const res = await fetch(`${BASE}/api/v1/audio/pipeline`, {
        method: "POST",
        body: form,
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || "Pipeline failed")
      }

      const data = await res.json()
      clearTimeout(t1); clearTimeout(t2); setStep(0)
      setResult(data)

      // Convert base64 audio to playable blob URL
      if (data.audio_b64) {
        const binary = atob(data.audio_b64)
        const bytes  = new Uint8Array(binary.length)
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
        const blob   = new Blob([bytes], { type: "audio/mpeg" })
        const url    = URL.createObjectURL(blob)
        setAudioUrl(url)
        setTimeout(() => audioRef.current?.play(), 300)
      }

    } catch (e) {
      clearTimeout(t1); clearTimeout(t2); setStep(0)
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  function handleDownload() {
    if (!audioUrl) return
    const a = document.createElement("a")
    a.href = audioUrl
    a.download = "translated_speech.mp3"
    a.click()
  }

  const steps = [
    { label: "Transcribe", desc: "Speech Recognition" },
    { label: "Translate",  desc: "deep-translator" },
    { label: "Synthesise", desc: "gTTS" },
  ]

  return (
    <div>
      <div className="section-header">
        <h2 className="section-title">Audio Pipeline</h2>
        <p className="section-desc">Upload audio in any language — get translated audio back automatically</p>
      </div>

      <div className="card">
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

        <div style={{ marginTop: "1rem" }}>
          <button
            className="btn btn-primary btn-lg"
            onClick={handleRun}
            disabled={loading || !file}
            style={{ width: "100%" }}
          >
            {loading ? <><span className="spinner" /> Processing…</> : "▶ Run Pipeline"}
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
          <audio ref={audioRef} src={audioUrl} controls style={{ width: "100%", marginTop: "0.5rem" }} />

          <div className="meta-row" style={{ marginTop: "0.75rem" }}>
            <span className="badge badge-green">{result.source_language} → {result.target_language}</span>
            <span className="badge badge-green">Provider: {result.translation_provider}</span>
            <span className="badge badge-green">Duration: {result.duration}s</span>
          </div>

          <div style={{ marginTop: "0.75rem" }}>
            <button className="btn btn-ghost" onClick={handleDownload}>
              ↓ Download Audio
            </button>
          </div>
        </div>
      )}
    </div>
  )
}