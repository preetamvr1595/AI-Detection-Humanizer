import { useState } from 'react'
import api from '../../api/client'
import TextToolShell from '../../components/TextToolShell'

export default function GrammarCheckerPage() {
  const [text, setText] = useState('')
  const [grammar, setGrammar] = useState(null)
  const [citation, setCitation] = useState(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')

  async function run() {
    setRunning(true)
    setError('')
    try {
      const [g, c] = await Promise.all([
        api.post('/tools/grammar-check', { text }),
        api.post('/tools/citation-check', { text }),
      ])
      setGrammar(g.data)
      setCitation(c.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Check failed.')
    } finally {
      setRunning(false)
    }
  }

  const readability = grammar?.readability || grammar

  return (
    <TextToolShell
      title="Grammar & Citations"
      subtitle="Real Flesch / Gunning Fog / SMOG readability formulas, rule-based grammar checks, and citation-format validation."
      text={text}
      setText={setText}
      onRun={run}
      running={running}
      actionLabel="Check"
      error={error}
    >
      {grammar && (
        <>
          <div className="score-cards">
            <div className="score-card fact">
              <div className="score-value">{readability?.flesch_reading_ease ?? '—'}</div>
              <div className="score-label">Flesch reading ease</div>
            </div>
            <div className="score-card plag">
              <div className="score-value">{readability?.flesch_kincaid_grade ?? '—'}</div>
              <div className="score-label">Flesch-Kincaid grade</div>
            </div>
            <div className="score-card ai">
              <div className="score-value">{grammar.total_issues ?? grammar.total_issues_found ?? 0}</div>
              <div className="score-label">Issues found</div>
            </div>
          </div>
          <p className="methodology-note">{readability?.grade_level_summary || readability?.grade_level_label}</p>

          {(grammar.structural_issues || grammar.grammar_issues || []).length > 0 && (
            <>
              <h2 className="section-title">Issues found</h2>
              <div className="matches-list">
                {(grammar.structural_issues || grammar.grammar_issues || []).slice(0, 20).map((issue, i) => (
                  <div className="match-row" key={i} style={{ gridTemplateColumns: '160px 1fr' }}>
                    <div className="match-type-tag">{issue.issue || issue.type}</div>
                    <div className="match-preview">{issue.context || issue.word}</div>
                  </div>
                ))}
              </div>
            </>
          )}

          {citation && (
            <>
              <h2 className="section-title">Citation check</h2>
              <p className="security-sub">
                Citation style detected: <strong>{citation.citation_style_detected || 'None detected'}</strong> ·{' '}
                Claims found: <strong>{citation.claims_detected}</strong> ·{' '}
                Uncited: <strong>{citation.uncited_claims?.length || 0}</strong> ·{' '}
                Coverage: <strong>{citation.citation_coverage_pct}%</strong>
              </p>
              <p className="methodology-note">{citation.limitation_note}</p>
            </>
          )}
        </>
      )}
    </TextToolShell>
  )
}
