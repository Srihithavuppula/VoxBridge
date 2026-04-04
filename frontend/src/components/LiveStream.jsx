// frontend/src/components/LiveStream.jsx
import { useState, useRef, useEffect } from "react"
import { createStreamWS, LANG_OPTIONS } from "../api"

export default function LiveStream() {
  const [sourceLang, setSource]   = useState("auto")
  const [targetLang, setTarget]   = useState("es")
  const [endpoint, setEndpoint]   = useState("pipeline")
  const [connected, setConnected] = useState(false)
  const [recording, setRecording] = useState(false)
  const [transcript, setTranscript] = useState("")
  const [translation, setTranslation] = useState("")
  const [status, setStatus]       = useState("Not connected")
  const [error, setError]         = useState("")
  const [audioQueue, setQueue]    = useState([])

  const wsRef       = useRef(null)
  const recorderRef = useRef(null)
  const audioRef    = useRef(null)

  useEffect(() => () => disconnect(), [])

  function connect() {
    setError(""); setTranscript(""); setTranslation("")
    const ws = createStreamWS({
      endpoint,
      source_language: sourceLang,
      target_language: targetLang,
      speak: endpoint === "pipeline",
    })

    ws.onopen = () => {
      setConnected(true)
      setStatus("Connected — ready to record")
    }

    ws.onclose = () => {
      setConnected(false); setRecording(false)
      setStatus("Disconnected")
    }

    ws.onerror = () => setError("WebSocket connection failed. Is the backend running?")

    ws.onmessage = async (event) => {
      if (event.data instanceof Blob) {
        // Audio bytes from TTS
        const url = URL.createObjectURL(event.data)
        const audio = new Audio(url)
        audio.play()
        return
      }
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === "transcript")  setTranscript(msg.text)
        if (msg.type === "translation") setTranslation(msg.text)
        if (msg.type === "status")      setStatus(msg.message)
        if (msg.type === "error")       setError(msg.message)
      } catch (_) {}
    }

    wsRef.current = ws
  }

  function disconnect() {
    stopRecording()
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({ action: "stop" }))
      wsRef.current.close()
      wsRef.current = null
    }
    setConnected(false)
    setStatus("Disconnected")
  }

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" })

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0 && wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(e.data)
        }
      }

      recorder.start(2000) // send chunk every 2 seconds
      recorderRef.current = recorder
      setRecording(true)
      setStatus("Recording… speak now")
    } catch (e) {
      setError("Microphone access denied. Please allow microphone in browser.")
    }
  }

  function stopRecording() {
    if (recorderRef.current) {
      recorderRef.current.stop()
      recorderRef.current.stream.getTracks().forEach(t => t.stop())
      recorderRef.current = null
    }
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: "flush" }))
    }
    setRecording(false)
    setStatus("Recording stopped")
  }

  function toggleRecording() {
    recording ? stopRecording() : startRecording()
  }

  return (
    <div>
      <div className="section-header">
        <h2 className="section-title">Live Stream</h2>
        <p className="section-desc">Real-time speech translation via WebSocket — speak and see results instantly</p>
      </div>

      <div className="card">
        {/* Config */}
        <div className="row" style={{ marginBottom: "1rem" }}>
          <div className="field" style={{ marginBottom: 0 }}>
            <label className="field-label">Mode</label>
            <select value={endpoint} onChange={e => setEndpoint(e.target.value)} disabled={connected}>
              <option value="stt">Transcribe only</option>
              <option value="translate">Transcribe + Translate</option>
              <option value="pipeline">Full Pipeline (+ Audio)</option>
            </select>
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label className="field-label">From</label>
            <select value={sourceLang} onChange={e => setSource(e.target.value)} disabled={connected}>
              {LANG_OPTIONS.map(l => <option key={l.code} value={l.code}>{l.name}</option>)}
            </select>
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label className="field-label">To</label>
            <select value={targetLang} onChange={e => setTarget(e.target.value)} disabled={connected}>
              {LANG_OPTIONS.filter(l => l.code !== "auto").map(l => (
                <option key={l.code} value={l.code}>{l.name}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Connect / Disconnect */}
        <div className="row-center" style={{ marginBottom: "1.5rem" }}>
          {!connected
            ? <button className="btn btn-primary" onClick={connect}>Connect</button>
            : <button className="btn btn-danger"  onClick={disconnect}>Disconnect</button>
          }
          <div className="status-row">
            <span className={`dot ${connected ? (recording ? "blue" : "green") : ""}`} />
            {status}
          </div>
        </div>

        {/* Mic button */}
        <div style={{ textAlign: "center" }}>
          <button
            className={`mic-btn ${recording ? "active" : ""}`}
            onClick={toggleRecording}
            disabled={!connected}
            title={recording ? "Stop recording" : "Start recording"}
          >
            {recording ? "⏹" : "🎤"}
          </button>
          <p style={{ marginTop: "0.5rem", fontSize: "0.8rem", color: "var(--text3)" }}>
            {recording ? "Recording… click to stop" : "Click to start recording"}
          </p>
        </div>

        {error && <div className="error-msg" style={{ marginTop: "1rem" }}>⚠ {error}</div>}
      </div>

      {/* Live results */}
      {(transcript || translation) && (
        <div className="card">
          <div className="row">
            <div>
              <label className="field-label" style={{ color: "var(--accent)" }}>📝 Transcript</label>
              <div className="live-box">
                {transcript || <span style={{ color: "var(--text3)" }}>Waiting…</span>}
              </div>
            </div>
            {endpoint !== "stt" && (
              <div>
                <label className="field-label" style={{ color: "var(--green)" }}>🌐 Translation</label>
                <div className="live-box">
                  {translation || <span style={{ color: "var(--text3)" }}>Waiting…</span>}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}