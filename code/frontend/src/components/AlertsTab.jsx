import { useCallback, useEffect, useState } from 'react'
import { api } from '../api.js'
import { AnimatedCard } from './shared.jsx'

const STATE_CLASS = { INFO: 'ok', WARNING: 'warn', CRITICAL: 'bad' }
function StatePill({ state }) {
  return <span className={`severity-badge severity-${STATE_CLASS[state] || 'ok'}`}>{state}</span>
}

const SEVERITIES = ['CRITICAL', 'WARNING', 'INFO']

export default function AlertsTab({ setError }) {
  const [alerts, setAlerts] = useState(null)
  const [severity, setSeverity] = useState('')
  const [showResolved, setShowResolved] = useState(false)

  const load = useCallback(() => {
    const params = {}
    if (severity) params.severity = severity
    if (!showResolved) params.resolved = 'false'
    api.alerts(params).then(setAlerts).catch((err) => setError(err.message))
  }, [severity, showResolved, setError])

  useEffect(() => { load() }, [load])

  const resolve = async (id) => {
    try {
      await api.resolveAlert(id)
      load()
    } catch (err) { setError(err.message) }
  }

  return (
    <div className="grid">
      <AnimatedCard title="Alerts" className="span-2">
        <p>Training/evaluation/deployment notifications (this platform Sec. 37-38) — Slack for informational events, PagerDuty for anything that blocks training or triggers a rollback.</p>
        <div className="uc-topic-filters">
          <button type="button" className={severity === '' ? 'uc-topic active' : 'uc-topic'} onClick={() => setSeverity('')}>All severities</button>
          {SEVERITIES.map((s) => (
            <button key={s} type="button" className={severity === s ? 'uc-topic active' : 'uc-topic'} onClick={() => setSeverity(s)}>{s}</button>
          ))}
          <label style={{ marginLeft: 'auto' }}>
            <input type="checkbox" checked={showResolved} onChange={(e) => setShowResolved(e.target.checked)} /> Show resolved
          </label>
        </div>
      </AnimatedCard>

      <AnimatedCard title={`${alerts ? alerts.length : 0} alerts`} className="span-2">
        <div className="table-wrap">
          <table>
            <thead><tr><th>Severity</th><th>Channel</th><th>Category</th><th>Message</th><th>Created</th><th>Resolved</th><th></th></tr></thead>
            <tbody>
              {(alerts || []).map((a) => (
                <tr key={a.id}>
                  <td><StatePill state={a.severity} /></td>
                  <td>{a.channel}</td>
                  <td>{a.category}</td>
                  <td>{a.message}</td>
                  <td className="muted">{new Date(a.created_at).toLocaleString()}</td>
                  <td>{a.resolved ? '✅' : '—'}</td>
                  <td>{!a.resolved && <button type="button" className="ghost-btn" onClick={() => resolve(a.id)}>Resolve</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {alerts && alerts.length === 0 && <p className="muted">No alerts match this filter.</p>}
        </div>
      </AnimatedCard>
    </div>
  )
}
