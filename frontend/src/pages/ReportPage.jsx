import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../api/client'
import Layout from '../components/Layout'

export default function ReportPage() {
  const { jobId } = useParams()
  const [job, setJob] = useState(null)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    api
      .get(`/documents/jobs/${jobId}`)
      .then(({ data }) => setJob(data))
      .catch(() => setError('Could not load this report.'))
  }, [jobId])

  async function downloadReport() {
    const res = await api.get(`/documents/jobs/${jobId}/report`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const a = document.createElement('a')
    a.href = url
    a.download = `ScholarShield_Report_${jobId.slice(0, 8)}.pdf`
    a.click()
    window.URL.revokeObjectURL(url)
  }

  if (error) {
    return (
      <Layout>
        <p className="form-error">{error}</p>
      </Layout>
    )
  }
  if (!job) {
    return (
      <Layout>
        <p>Loading report…</p>
      </Layout>
    )
  }

  const ai = job.ai_detection_detail
  const grammar = job.grammar_readability_detail
  const readability = grammar?.readability || grammar
  const citation = job.citation_detail
  const paraphrase = job.paraphrase_detail

  return (
    <Layout>
      <button className="btn-ghost back-link" onClick={() => navigate('/documents')}>
        ← Back to document scan
      </button>
      <div className="page-header">
        <h1>{job.file_name || 'Document'}</h1>
        <p>Status: {job.status}</p>
      </div>

      {job.status === 'COMPLETE' ? (
        <>
          {job.extraction_diagnostics?.low_confidence_extraction && (
            <div className="extraction-warning-banner">
              <strong>⚠ Low-confidence extraction:</strong> {job.extraction_diagnostics.warning}
              <div className="extraction-warning-detail">
                {job.extraction_diagnostics.extracted_word_count} words extracted ·
                {' '}method: {job.extraction_diagnostics.extraction_method?.join(', ')}
                {job.extraction_diagnostics.pages_ocr_fallback > 0 &&
                  ` · OCR used on ${job.extraction_diagnostics.pages_ocr_fallback} page(s)`}
              </div>
            </div>
          )}

          <div className="score-cards">
            <div className="score-card ai">
              <div className="score-value">{job.ai_score}%</div>
              <div className="score-label">AI-generation probability</div>
            </div>
            <div className="score-card plag">
              <div className="score-value">{job.plagiarism_score}%</div>
              <div className="score-label">Plagiarism similarity</div>
            </div>
            <div className="score-card fact">
              <div className="score-value">{job.fact_check_score != null ? `${job.fact_check_score}%` : '—'}</div>
              <div className="score-label">Citation coverage</div>
            </div>
          </div>

          {ai && (
            <>
              <h2 className="section-title">AI Detector Suite — Multi-Model Consensus</h2>
              <div className="detector-grid">
                <div className="detector-card">
                  <div className="detector-title">Detector 1 · Perplexity</div>
                  <div className="detector-value">{ai.detector_1_perplexity?.ai_probability}%</div>
                  <div className="detector-sub">confidence {ai.detector_1_perplexity?.confidence}%</div>
                </div>
                <div className="detector-card">
                  <div className="detector-title">Detector 2 · Stylometry</div>
                  <div className="detector-value">{ai.detector_2_stylometry?.human_style_score}%</div>
                  <div className="detector-sub">human style score</div>
                </div>
                <div className="detector-card">
                  <div className="detector-title">Detector 3 · Family classifier</div>
                  <div className="detector-value">{ai.detector_3_family_classifier?.most_likely_family}</div>
                  <div className="detector-sub">most likely origin</div>
                </div>
              </div>
              {ai.detector_3_family_classifier?.family_distribution && (
                <div className="family-bars">
                  {Object.entries(ai.detector_3_family_classifier.family_distribution).map(([fam, pct]) => (
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
              <p className="methodology-note">{ai.methodology_note}</p>
            </>
          )}

          <h2 className="section-title">Plagiarism matches</h2>
          {job.plagiarism_matches.length === 0 ? (
            <p className="empty-state">No significant matches found against the reference corpus.</p>
          ) : (
            <div className="matches-list">
              {job.plagiarism_matches.map((m, i) => (
                <div className="match-row" key={i}>
                  <div className="match-source">{m.matched_source}</div>
                  <div className="match-score">{m.similarity_score}%</div>
                  <div className="match-type-tag">{m.match_type}</div>
                  <div className="match-preview">{m.segment_preview}</div>
                </div>
              ))}
            </div>
          )}

          {paraphrase && (
            <>
              <h2 className="section-title">Auto-paraphraser (triggered — overlap above threshold)</h2>
              <div className="paraphrase-card">
                <div className="paraphrase-meta">
                  <span>Mode: <strong>{paraphrase.mode}</strong></span>
                  <span>Fact preservation: <strong className={paraphrase.fact_preservation.preserved ? 'ok-text' : 'warn-text'}>
                    {paraphrase.fact_preservation.preserved ? 'PASSED' : 'FAILED'}
                  </strong></span>
                  <span>Lexical change: <strong>{paraphrase.lexical_change_pct}%</strong></span>
                </div>
                <p className="paraphrase-text">{paraphrase.rewritten_text}</p>
              </div>
            </>
          )}

          {readability && (
            <>
              <h2 className="section-title">Grammar &amp; readability</h2>
              <div className="score-cards">
                <div className="score-card fact">
                  <div className="score-value">{readability.flesch_reading_ease ?? '—'}</div>
                  <div className="score-label">Flesch reading ease</div>
                </div>
                <div className="score-card plag">
                  <div className="score-value">{readability.flesch_kincaid_grade ?? '—'}</div>
                  <div className="score-label">Flesch-Kincaid grade</div>
                </div>
                <div className="score-card ai">
                  <div className="score-value">{grammar.total_issues ?? grammar.total_issues_found ?? 0}</div>
                  <div className="score-label">Issues found</div>
                </div>
              </div>
              <p className="methodology-note">{readability.grade_level_summary || readability.grade_level_label}</p>
            </>
          )}

          {citation && (
            <>
              <h2 className="section-title">Fact &amp; citation check</h2>
              <p className="security-sub">
                Citation style detected: <strong>{citation.citation_style_detected || 'None detected'}</strong> ·
                {' '}Claims found: <strong>{citation.claims_detected}</strong> ·
                {' '}Uncited: <strong>{citation.uncited_claims?.length || 0}</strong>
              </p>
              <p className="methodology-note">{citation.limitation_note}</p>
            </>
          )}

          <button className="btn-primary" onClick={downloadReport}>
            Download signed &amp; encrypted PDF report
          </button>
        </>
      ) : (
        <p>This document is still being analyzed. Refresh in a moment.</p>
      )}
    </Layout>
  )
}
