import Layout from './Layout'

export default function TextToolShell({
  title, subtitle, text, setText, onRun, running, actionLabel, error, children, extraControls,
}) {
  const words = text.trim() ? text.trim().split(/\s+/).length : 0
  const chars = text.length

  return (
    <Layout>
      <div className="page-header">
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>

      <div className="tool-input-card">
        <textarea
          className="tool-textarea"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste or type your text here…"
          rows={12}
        />
        <div className="tool-input-footer">
          <span className="tool-word-count">{words} words · {chars} characters</span>
          <div className="tool-input-actions">
            {extraControls}
            <button className="btn-primary" style={{ width: 'auto' }} onClick={onRun} disabled={running || words < 15}>
              {running ? 'Working…' : actionLabel}
            </button>
          </div>
        </div>
        {words > 0 && words < 15 && <p className="tool-hint">Enter at least 15 words for a reliable result.</p>}
        {error && <div className="form-error">{error}</div>}
      </div>

      {children}
    </Layout>
  )
}
