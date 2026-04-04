// frontend/src/components/TextTranslation.jsx
import { useState } from "react"
import { translateText, LANG_OPTIONS } from "../api"

export default function TextTranslation() {
  const [text, setText] = useState("")
  const [result, setResult] = useState(null)
  const [sourceLang, setSource] = useState("en")
  const [targetLang, setTarget] = useState("es")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  async function handleTranslate() {
    if (!text.trim()) return
    setLoading(true); setError(""); setResult(null)
    try {
      const data = await translateText({
        text: text.trim(),
        source_language: sourceLang,
        target_language: targetLang,
      })
      setResult(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  function swap() {
    if (sourceLang === "auto") return
    setSource(targetLang)
    setTarget(sourceLang)
    setResult(null)
  }

  return (
    <div>
      <div className="section-header">
        <h2 className="section-title">Text to Text</h2>
        <p className="section-desc">Translate text between 100+ languages instantly</p>
      </div>

      <div className="card">
        {/* Language selectors */}
        <div
          className="row"
          style={{
            marginBottom: "1rem",
            alignItems: "flex-start",
            flexDirection: "column", // Stack for mobile first
            gap: "0.5rem",
          }}
        >
          <div className="field" style={{ marginBottom: 0, width: "100%" }}>
            <label className="field-label">Source Language</label>
            <select
              value={sourceLang}
              onChange={e => setSource(e.target.value)}
              style={{
                width: "100vw",
                maxWidth: "100%",
                minWidth: "0",
                boxSizing: "border-box",
                marginLeft: "-16px", // To offset padding if inside a card with padding
              }}
            >
              {LANG_OPTIONS.map(l => (
                <option key={l.code} value={l.code}>{l.name}</option>
              ))}
            </select>
          </div>

          <div
            style={{
              width: "100%",
              display: "flex",
              justifyContent: "center",
              margin: "0.5rem 0",
            }}
          >
            <button className="btn btn-ghost" onClick={swap} title="Swap languages" style={{ width: "48px" }}>
              ⇄
            </button>
          </div>

          <div className="field" style={{ marginBottom: 0, width: "100%" }}>
            <label className="field-label">Target Language</label>
            <select
              value={targetLang}
              onChange={e => setTarget(e.target.value)}
              style={{
                width: "100vw",
                maxWidth: "100%",
                minWidth: "0",
                boxSizing: "border-box",
                marginLeft: "-16px", // To offset padding if inside a card with padding
              }}
            >
              {LANG_OPTIONS.filter(l => l.code !== "auto").map(l => (
                <option key={l.code} value={l.code}>{l.name}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Input */}
        <div className="field">
          <label className="field-label">Source Text</label>
          <textarea
            value={text}
            onChange={e => setText(e.target.value)}
            placeholder="Type or paste text to translate…"
            rows={5}
          />
          <div style={{ textAlign: "right", fontSize: "0.75rem", color: "var(--text3)", marginTop: "4px" }}>
            {text.length} / 5000
          </div>
        </div>

        <button
          className="btn btn-primary"
          onClick={handleTranslate}
          disabled={loading || !text.trim()}
        >
          {loading ? <><span className="spinner" /> Translating…</> : "Translate"}
        </button>
      </div>

      {/* Result */}
      {(result || error) && (
        <div className="card">
          <label className="field-label">Translation</label>
          {error
            ? <div className="error-msg">⚠ {error}</div>
            : <>
              <div className="result-box">{result.translated_text}</div>
              <div className="meta-row">
                <span className="badge badge-blue">Provider: {result.provider}</span>
                <span className="badge badge-blue">{result.source_language} → {result.target_language}</span>
                <span className="badge badge-blue">{result.character_count} chars</span>
              </div>
            </>
          }
        </div>
      )}
    </div>
  )
}