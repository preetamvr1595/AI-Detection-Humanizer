import { useState } from 'react'
import api from '../../api/client'
import TextToolShell from '../../components/TextToolShell'
import ScoreGauge from '../../components/ScoreGauge'

function highlightColor(score) {
  if (score == null) return 'transparent'
  if (score < 30) return 'rgba(221, 214, 254, 0.45)'
  if (score < 60) return 'rgba(192, 132, 252, 0.35)'
  return 'rgba(147, 51, 234, 0.30)'
}

function badgeClass(score) {
  if (score < 30) return 'ok-badge'
  if (score < 60) return 'warn-badge'
  return 'danger-badge'
}

export default function AIDetectorPage() {
  const [text, setText] = useState('')
  const [result, setResult] = useState(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')

  async function run() {
    setRunning(true)
    setError('')
    try {
      const { data } = await api.post('/tools/detect-ai', { text })
      setResult(data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Detection failed.')
    } finally {
      setRunning(false)
    }
  }

  return (
    <TextToolShell
      title="AI Detector"
      subtitle="Multi-model consensus: perplexity proxy, stylometry, Zipf distribution fit, and model-family classifier."
      text={text}
      setText={setText}
      onRun={run}
      running={running}
      actionLabel="Detect AI"
      error={error}
    >
      {result && (
        <>
          <div className="tool-result-card">
            <ScoreGauge value={result.ai_probability} label="AI-generation probability" color={result.ai_probability > 50 ? '#7c3aed' : '#9333ea'} />
            <div className="detector-grid" style={{ flex: 1 }}>
              <div className="detector-card">
                <div className="detector-title">Detector 1 · Perplexity</div>
                <div className="detector-value">{result.detector_1_perplexity?.ai_probability}%</div>
                <div className="detector-sub">confidence {result.detector_1_perplexity?.confidence}%</div>
              </div>
              <div className="detector-card">
                <div className="detector-title">Detector 2 · Stylometry</div>
                <div className="detector-value">{result.detector_2_stylometry?.human_style_score}%</div>
                <div className="detector-sub">human style score</div>
              </div>
              <div className="detector-card">
                <div className="detector-title">Detector 3 · Family</div>
                <div className="detector-value">{result.detector_3_family_classifier?.most_likely_family}</div>
                <div className="detector-sub">most likely origin</div>
              </div>
            </div>
          </div>

          {result.detector_3_family_classifier?.family_distribution && (
            <div className="family-bars">
              {Object.entries(result.detector_3_family_classifier.family_distribution).map(([fam, pct]) => (
                <div className="family-bar-row" key={fam}>
                  <span className="family-bar-label">{fam}</span>
                  <div className="family-bar-track">
                    <div className="family-bar-fill" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="family-bar-pct">{pct}%</span>
                </div>
              ))}
            </div>
          )}

          {result.signals && (
            <div className="diagnostic-section" style={{ marginTop: 24 }}>
              <h2 className="section-title">Stylometric Diagnostics</h2>
              <div className="detector-grid">
                <div className="detector-card" title="Measures sentence length variation. Higher variation (burstiness) is highly human-like.">
                  <div className="detector-title">Sentence Burstiness</div>
                  <div className="detector-value">
                    {result.signals.burstiness != null ? result.signals.burstiness : 'N/A'}
                  </div>
                  <div className="detector-sub">
                    {result.signals.burstiness >= 7.0 ? 'Highly Bursty (Human)' : result.signals.burstiness >= 4.0 ? 'Moderate' : 'Uniform (AI-like)'}
                  </div>
                </div>

                <div className="detector-card" title="Measures vocabulary richness using Herdan's C (bilogarithmic TTR).">
                  <div className="detector-title">Vocabulary Richness</div>
                  <div className="detector-value">
                    {result.signals.lexical_diversity != null ? (100 - result.signals.lexical_diversity).toFixed(1) + '%' : 'N/A'}
                  </div>
                  <div className="detector-sub">
                    {result.signals.lexical_diversity < 35 ? 'Rich (Human-like)' : result.signals.lexical_diversity < 65 ? 'Standard' : 'Repetitive (AI-like)'}
                  </div>
                </div>

                <div className="detector-card" title="Counts spelling mistakes and typo footprints. Humans make typos; AI has perfect spelling.">
                  <div className="detector-title">Typographical Errors</div>
                  <div className="detector-value">
                    {result.signals.typo_density != null ? result.signals.typo_density.toFixed(2) + '%' : '0.00%'}
                  </div>
                  <div className="detector-sub">
                    {result.signals.typo_density > 0.5 ? 'Natural (Human)' : 'Zero/Perfect (AI-like)'}
                  </div>
                </div>

                <div className="detector-card" title="Counts the occurrences of typical AI logical connectives and clichés.">
                  <div className="detector-title">AI Cliches Detected</div>
                  <div className="detector-value">
                    {result.signals.cliche_density != null ? result.signals.cliche_density : 0}
                  </div>
                  <div className="detector-sub">
                    {result.signals.cliche_density > 1.8 ? 'Excessive (AI-like)' : result.signals.cliche_density > 0.8 ? 'Standard' : 'Low (Human-like)'}
                  </div>
                </div>
              </div>
            </div>
          )}

          <h2 className="section-title" style={{ marginTop: 24 }}>Sentence-by-sentence analysis</h2>
          {result.sentence_breakdown && result.sentence_breakdown.length > 0 ? (
            <div className="sentence-list" style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 12 }}>
              {result.sentence_breakdown.map((h, i) => (
                <div
                  key={i}
                  style={{
                    display: 'flex',
                    alignItems: 'baseline',
                    gap: 12,
                    padding: '10px 14px',
                    borderRadius: 8,
                    backgroundColor: highlightColor(h.ai_likelihood),
                    borderLeft: `4px solid ${h.ai_likelihood > 50 ? '#7c3aed' : '#a855f7'}`
                  }}
                >
                  <span style={{ fontSize: '0.8rem', fontWeight: 600, opacity: 0.6, minWidth: 32 }}>#{i + 1}</span>
                  <span style={{ flex: 1, fontSize: '0.95rem', lineHeight: '1.5' }}>{h.sentence}</span>
                  <span
                    style={{
                      fontSize: '0.78rem',
                      fontWeight: 600,
                      padding: '3px 10px',
                      borderRadius: 6,
                      backgroundColor: h.ai_likelihood > 50 ? 'rgba(124, 58, 237, 0.15)' : 'rgba(168, 85, 247, 0.15)',
                      color: h.ai_likelihood > 50 ? '#6b21a8' : '#7c3aed',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    {h.ai_likelihood}% AI
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="highlighted-text">
              {result.sentence_breakdown?.map((h, i) => (
                <span key={i} style={{ backgroundColor: highlightColor(h.ai_likelihood) }} title={`${h.ai_likelihood}% AI-like`}>
                  {h.sentence}{' '}
                </span>
              ))}
            </div>
          )}

          <p className="methodology-note" style={{ marginTop: 20 }}>{result.methodology_note}</p>
        </>
      )}
    </TextToolShell>
  )
}
