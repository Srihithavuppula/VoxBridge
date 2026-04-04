// frontend/src/App.jsx
import { useState } from "react"
import TextTranslation from "./components/TextTranslation"
import AudioTranscribe from "./components/AudioTranscribe"
import TextToSpeech from "./components/TextToSpeech"
import LiveStream from "./components/LiveStream"
import AudioPipeline from "./components/AudioPipeline"
import "./App.css"

const TABS = [
  { id: "text", label: "Text to Text", icon: "⇄" },
  { id: "transcribe", label: "Audio to Text", icon: "◎" },
  { id: "tts", label: "Text to Audio", icon: "▶" },
  { id: "pipeline", label: "Audio to Audio", icon: "↻" },
  { id: "stream", label: "Live Stream", icon: "⬤" },
]

export default function App() {
  const [active, setActive] = useState("text")

  return (
    <div className="app">
      <header className="header">
        <div className="header-inner">
          <div className="brand">
            <span className="brand-icon">⬡</span>
            <div>
              <h1 className="brand-name">VoxBridge</h1>
              <p className="brand-sub">Multilingual Speech Translation</p>
            </div>
          </div>
          <div className="status-dot" title="Backend connected" />
        </div>
      </header>

      <nav className="nav">
        <div className="nav-inner">
          {TABS.map(tab => (
            <button
              key={tab.id}
              className={`nav-btn ${active === tab.id ? "active" : ""}`}
              onClick={() => setActive(tab.id)}
            >
              <span className="nav-icon">{tab.icon}</span>
              <span className="nav-label">{tab.label}</span>
            </button>
          ))}
        </div>
      </nav>

      <main className="main">
        <div className="panel">
          {active === "text" && <TextTranslation />}
          {active === "transcribe" && <AudioTranscribe />}
          {active === "tts" && <TextToSpeech />}
          {active === "pipeline" && <AudioPipeline />}
          {active === "stream" && <LiveStream />}
        </div>
      </main>
    </div>
  )
}