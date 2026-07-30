import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import api from '../api/client'
import Layout from '../components/Layout'

export default function AdminPage() {
  const [summary, setSummary] = useState(null)
  const [logs, setLogs] = useState([])
  const [chainStatus, setChainStatus] = useState(null)
  const [checking, setChecking] = useState(false)

  useEffect(() => {
    api.get('/admin/summary').then(({ data }) => setSummary(data))
    api.get('/admin/audit-logs').then(({ data }) => setLogs(data))
  }, [])

  async function verifyChain() {
    setChecking(true)
    try {
      const { data } = await api.get('/admin/audit-logs/verify')
      setChainStatus(data)
    } finally {
      setChecking(false)
    }
  }

  const chartData = summary
    ? [
        { name: 'AI-flagged', value: summary.ai_flagged_rate },
        { name: 'Avg. plagiarism', value: summary.avg_plagiarism_score },
      ]
    : []

  return (
    <Layout>
      <div className="page-header">
        <h1>Admin analytics</h1>
        <p>Platform-wide submission and security metrics.</p>
      </div>

      {summary && (
        <div className="score-cards">
          <div className="score-card ai">
            <div className="score-value">{summary.total_submissions}</div>
            <div className="score-label">Total submissions</div>
          </div>
          <div className="score-card plag">
            <div className="score-value">{summary.ai_flagged_rate}%</div>
            <div className="score-label">AI-flagged rate</div>
          </div>
          <div className="score-card fact">
            <div className="score-value">{summary.security_incidents}</div>
            <div className="score-label">Security incidents (infected uploads)</div>
          </div>
        </div>
      )}

      <h2 className="section-title">Detection rates</h2>
      <div className="chart-card">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2b3a4a" />
            <XAxis dataKey="name" stroke="#9fb2c3" />
            <YAxis stroke="#9fb2c3" />
            <Tooltip contentStyle={{ background: '#1b2733', border: '1px solid #33475B' }} />
            <Bar dataKey="value" fill="#3B82C4" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <h2 className="section-title">Tamper-evident audit chain</h2>
      <div className="security-card">
        <div className="security-row">
          <div>
            <div className="security-label">Hash-chained audit log integrity</div>
            <div className="security-sub">
              Every audit entry embeds the SHA-256 hash of the entry before it. Verifying walks
              the full chain and recomputes every hash from stored content.
            </div>
          </div>
          <button className="btn-primary" style={{ width: 'auto' }} onClick={verifyChain} disabled={checking}>
            {checking ? 'Verifying…' : 'Verify chain'}
          </button>
        </div>
        {chainStatus && (
          <p className={chainStatus.valid ? 'security-status' : 'form-error'}>
            {chainStatus.valid
              ? `✓ Chain valid — ${chainStatus.entries_checked} entries checked, no tampering detected.`
              : `✗ Chain broken at entry ${chainStatus.broken_at}: ${chainStatus.reason}`}
          </p>
        )}
      </div>

      <h2 className="section-title">Audit log</h2>
      <div className="audit-list">
        {logs.map((l) => (
          <div className="audit-row" key={l.log_id}>
            <span className="audit-action">{l.action}</span>
            <span className="audit-resource">{l.resource}</span>
            <span className="audit-time">{new Date(l.timestamp).toLocaleString()}</span>
          </div>
        ))}
      </div>
    </Layout>
  )
}
