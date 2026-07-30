import { useState } from 'react'
import api from '../../api/client'
import TextToolShell from '../../components/TextToolShell'
import ScoreGauge from '../../components/ScoreGauge'

export default function PlagiarismCheckerPage() {
  const [text, setText] = useState('')
  const [result, setResult] = useState(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')

  async function run() {
    setRunning(true)
    setError('')
    try {
      const { data } = await api.post('/tools/check-plagiarism', { text })
      setResult(data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Check failed.')
    } finally {
      setRunning(false)
    }
  }

  return (
    <TextToolShell
      title="Plagiarism Checker"
      subtitle="Hybrid structural (word-shingle) + lexical-semantic (TF-IDF) matching against a reference corpus."
      text={text}
      setText={setText}
      onRun={run}
      running={running}
      actionLabel="Check Plagiarism"
      error={error}
    >
      {result && (
        <>
          <div className="tool-result-card tool-result-single">
            <ScoreGauge value={result.plagiarism_score} label="Overall similarity" color="#7c3aed" />
          </div>

          <h2 className="section-title">Matched sources</h2>
          {result.matches.length === 0 ? (
            <p className="empty-state">No significant matches found against the reference corpus.</p>
          ) : (
            <div className="matches-list">
              {result.matches.map((m, i) => (
                <div className="match-row" key={i}>
                  <div className="match-source">{m.matched_source}</div>
                  <div className="match-score">{m.similarity_score}%</div>
                  <div className="match-type-tag">{m.match_type}</div>
                  <div className="match-preview">{m.segment_preview}</div>
                </div>
              ))}
            </div>
          )}
          <p className="methodology-note">{result.methodology_note}</p>
        </>
      )}
    </TextToolShell>
  )
}
