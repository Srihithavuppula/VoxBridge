// frontend/src/components/AudioTranscribe.jsx
import { useState, useRef } from "react"
import { transcribeAudio, LANG_OPTIONS } from "../api"

export default function AudioTranscribe() {
  const [file, setFile] = useState(null)
  const [lang, setLang] = useState("")
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [drag, setDrag] = useState(false)
  const inputRef = useRef()

  function onFile(f) {
    if (!f) return
    setFile(f); setResult(null); setError("")
  }

  async function handleTranscribe() {
    if (!file) return
    setLoading(true); setError(""); setResult(null)
    try {
      const data = await transcribeAudio({ file, language: lang })
      setResult(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="section-header">
        <h2 className="section-title">Audio to Text</h2>
        <p className="section-desc">Upload an audio file and get text using Whisper AI (runs locally)</p>
      </div>

      <div className="card">
        {/* Upload area */}
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
            : <p className="upload-text"><strong>Click to upload</strong> or drag and drop<br />mp3, wav, ogg, webm, flac — max 25MB</p>
          }
          <input
            ref={inputRef}
            type="file"
            accept=".mp3,.wav,.ogg,.webm,.flac,.m4a"
            style={{ display: "none" }}
            onChange={e => onFile(e.target.files[0])}
          />
        </div>

        {/* Language hint */}
        <div className="field" style={{ marginTop: "1rem" }}>
          <label className="field-label">Language Hint (optional)</label>
          <select value={lang} onChange={e => setLang(e.target.value)}>
            <option value="">Auto detect</option>
            {LANG_OPTIONS.filter(l => l.code !== "auto").map(l => (
              <option key={l.code} value={l.code}>{l.name}</option>
            ))}
          </select>
        </div>

        <button
          className="btn btn-primary"
          onClick={handleTranscribe}
          disabled={loading || !file}
        >
          {loading ? <><span className="spinner" /> Transcribing…</> : "Transcribe"}
        </button>

        {loading && (
          <p style={{ marginTop: "0.75rem", fontSize: "0.8rem", color: "var(--text3)" }}>
            ⏳ First run may take a moment while Whisper loads…
          </p>
        )}
      </div>

      {/* Result */}
      {(result || error) && (
        <div className="card">
          <label className="field-label">Transcript</label>
          {error
            ? <div className="error-msg">⚠ {error}</div>
            : <>
              <div className="result-box">{result.transcript}</div>
              <div className="meta-row">
                <span className="badge badge-green">Language: {result.language}</span>
                <span className="badge badge-green">Duration: {result.duration}s</span>
                <span className="badge badge-green">Model: whisper-{result.model}</span>
              </div>
            </>
          }
        </div>
      )}
    </div>
  )
}