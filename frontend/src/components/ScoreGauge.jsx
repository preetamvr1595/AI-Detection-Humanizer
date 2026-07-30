export default function ScoreGauge({ value, label, color = '#7c3aed', size = 160 }) {
  const pct = Math.max(0, Math.min(100, value ?? 0))
  const track = '#ede9fe'
  const style = {
    width: size,
    height: size,
    borderRadius: '50%',
    background: `conic-gradient(${color} ${pct * 3.6}deg, ${track} ${pct * 3.6}deg)`,
  }
  return (
    <div className="score-gauge-wrap">
      <div className="score-gauge-outer" style={style}>
        <div className="score-gauge-inner">
          <div className="score-gauge-value">{value != null ? `${value}%` : '—'}</div>
        </div>
      </div>
      {label && <div className="score-gauge-label">{label}</div>}
    </div>
  )
}
