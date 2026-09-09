export function StatusDot({ ok, label }) {
  return (
    <span className={`status-dot ${ok ? 'ok' : 'bad'}`}>
      <span className="status-dot-mark" />
      {label}
    </span>
  )
}

export function AnimatedCard({ title, className = '', children }) {
  return (
    <section className={`card animate-in ${className}`}>
      {title && <h3>{title}</h3>}
      {children}
    </section>
  )
}

export function ProgressBar({ value, max = 1, color }) {
  const pct = Math.round((value / max) * 100)
  return (
    <div className="mini-progress" aria-hidden="true">
      <div className="mini-progress-fill" style={{ width: `${pct}%`, background: color }} />
    </div>
  )
}

const SEVERITY_TONES = { CRITICAL: 'bad', HIGH: 'bad', MEDIUM: 'warn', LOW: 'ok', INFO: 'ok' }

export function SeverityBadge({ severity }) {
  const tone = SEVERITY_TONES[severity] || 'ok'
  return <span className={`severity-badge severity-${tone}`}>{severity}</span>
}
