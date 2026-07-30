import { useNavigate } from 'react-router-dom'
import Layout from '../components/Layout'

const TOOLS = [
  {
    to: '/tools/ai-detector',
    icon: '◈',
    title: 'AI Detector',
    desc: 'Paste any text to get a multi-model consensus AI-generation probability, with sentence-by-sentence highlighting.',
    color: '#7c3aed',
  },
  {
    to: '/tools/humanizer',
    icon: '✎',
    title: 'Humanizer',
    desc: 'Rewrite AI-flagged text to reduce its detection score, with a hard guarantee that no fact, number, or name is changed.',
    color: '#9333ea',
  },
  {
    to: '/tools/plagiarism',
    icon: '⧉',
    title: 'Plagiarism Checker',
    desc: 'Hybrid structural + lexical-semantic matching against a reference corpus, with a full source match breakdown.',
    color: '#6b21a8',
  },
  {
    to: '/tools/grammar',
    icon: '✓',
    title: 'Grammar & Citations',
    desc: 'Flesch/Gunning Fog/SMOG readability scoring, rule-based grammar checks, and citation-format validation.',
    color: '#a855f7',
  },
]

export default function ToolsHubPage() {
  const navigate = useNavigate()
  return (
    <Layout>
      <div className="page-header">
        <h1>Tools</h1>
        <p>Paste text into any tool below for an instant result — no file upload required.</p>
      </div>
      <div className="tools-grid">
        {TOOLS.map((t) => (
          <div key={t.to} className="tool-card" onClick={() => navigate(t.to)} style={{ '--tool-color': t.color }}>
            <div className="tool-card-icon">{t.icon}</div>
            <div className="tool-card-title">{t.title}</div>
            <div className="tool-card-desc">{t.desc}</div>
            <div className="tool-card-cta">Open tool →</div>
          </div>
        ))}
      </div>

      <h2 className="section-title">Prefer a full document scan?</h2>
      <p className="security-sub" style={{ marginBottom: 16 }}>
        Upload a PDF/DOCX/TXT file to run it through the real ClamAV + YARA security gateway,
        then all four modules at once, with a signed, encrypted PDF report you can download.
      </p>
      <button className="btn-ghost" onClick={() => navigate('/documents')}>Go to Document Scan →</button>
    </Layout>
  )
}
