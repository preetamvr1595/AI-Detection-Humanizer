import { useState } from 'react'
import api from '../../api/client'
import TextToolShell from '../../components/TextToolShell'
import ScoreGauge from '../../components/ScoreGauge'

const MODES = [
  { value: 'academic', label: 'Academic' },
  { value: 'professional', label: 'Professional' },
  { value: 'short_form', label: 'Short-form / Blog' },
  { value: 'structural', label: 'Structural' },
]

export default function HumanizerPage() {
  const [text, setText] = useState('')
  const [mode, setMode] = useState('academic')
  const [result, setResult] = useState(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)

  async function run() {
    setRunning(true)
    setError('')
    setCopied(false)
    try {
      const { data } = await api.post('/tools/humanize', { text, mode })
      setResult(data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Humanizing failed.')
    } finally {
      setRunning(false)
    }
  }

  function copyResult() {
    navigator.clipboard.writeText(result.rewritten_text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const modeSelector = (
    <select className="mode-select" value={mode} onChange={(e) => setMode(e.target.value)}>
      {MODES.map((m) => (
        <option key={m.value} value={m.value}>{m.label}</option>
      ))}
    </select>
  )

  return (
    <TextToolShell
      title="Humanizer"
      subtitle="Rewrites AI-flagged phrasing, rotates cliché buzzwords, and varies sentence lengths to inject natural burstiness while guaranteeing every number, date, and name is preserved exactly."
      text={text}
      setText={setText}
      onRun={run}
      running={running}
      actionLabel="Humanize"
      error={error}
      extraControls={modeSelector}
    >
      {result && (
        <>
          <div className="tool-result-card">
            <ScoreGauge value={result.ai_probability_before} label="Before" color="#6b21a8" size={130} />
            <div className="humanize-arrow">→</div>
            <ScoreGauge value={result.ai_probability_after} label="After" color="#a855f7" size={130} />
            <div className="humanize-delta">
              <div className={`humanize-delta-value ${result.ai_probability_delta >= 0 ? 'ok-text' : 'warn-text'}`}>
                {result.ai_probability_delta >= 0 ? '−' : '+'}{Math.abs(result.ai_probability_delta)}%
              </div>
              <div className="detector-sub">AI-detection change</div>
            </div>
          </div>

          <div className="fact-check-banner">
            <span className={result.fact_preservation.preserved ? 'ok-text' : 'warn-text'}>
              {result.fact_preservation.preserved ? '✓ All facts, numbers, and names preserved exactly' : '✗ Fact-preservation check failed — original wording kept'}
            </span>
          </div>

          <h2 className="section-title">Rewritten text</h2>
          <div className="paraphrase-card">
            <p className="paraphrase-text">{result.rewritten_text}</p>
          </div>
          <button className="btn-ghost" onClick={copyResult}>{copied ? 'Copied!' : 'Copy rewritten text'}</button>

          <p className="methodology-note" style={{ marginTop: 16 }}>
            Advanced rule-based humanization (WordNet synonym rotation, targeted AI buzzword replacement, and sentence-splitting burstiness injection), not a generative
            model — fact preservation is fully guaranteed. {result.sentences_rejected_for_fact_risk > 0 &&
              `${result.sentences_rejected_for_fact_risk} sentence(s) were left unchanged because rewriting them risked altering a fact.`}
          </p>
        </>
      )}
    </TextToolShell>
  )
}
