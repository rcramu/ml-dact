import { useCallback, useEffect, useState } from 'react'
import { api } from '../api.js'
import { AnimatedCard } from './shared.jsx'

const CANARY_ORDER = ['stage', 'smoke_test', 'canary_5', 'canary_25', 'canary_50', 'canary_100', 'production']

export default function DeploymentTab({ setError, selectedModel, setSelectedModel }) {
  const [models, setModels] = useState([])
  const [chosenModel, setChosenModel] = useState('')
  const [deployment, setDeployment] = useState(null)
  const [sla, setSla] = useState(null)
  const [reason, setReason] = useState('Manual rollback requested from the Deployment & Rollback tab')
  const [rollingBack, setRollingBack] = useState(false)

  useEffect(() => {
    api.models().then((rows) => {
      setModels(rows)
      const initial = selectedModel || rows[0]?.name
      if (initial) setChosenModel(initial)
    }).catch((err) => setError(err.message))
  }, [selectedModel, setError])

  const loadDeployment = useCallback(() => {
    if (!chosenModel) return
    api.deployment(chosenModel).then(setDeployment).catch((err) => setError(err.message))
  }, [chosenModel, setError])

  useEffect(() => { loadDeployment() }, [loadDeployment])
  useEffect(() => { api.sla().then(setSla).catch((err) => setError(err.message)) }, [setError])

  const doRollback = async () => {
    setRollingBack(true)
    try {
      await api.rollback(chosenModel, reason)
      loadDeployment()
    } catch (err) { setError(err.message) } finally { setRollingBack(false) }
  }

  // Group deployment events by the version that most recently reached each canary stage (latest wins).
  const canaryByStage = {}
  ;(deployment?.events || []).slice().reverse().forEach((e) => {
    if (CANARY_ORDER.includes(e.stage)) canaryByStage[e.stage] = e
  })

  return (
    <div className="grid">
      <AnimatedCard title="Deployment & Rollback" className="span-2">
        <p>Every promoted candidate progresses through a canary rollout (this platform Sec. 25) before serving 100% of traffic. If a production regression is detected, the pipeline automatically restores the previous champion (this platform Sec. 26-27).</p>
        <div className="trigger-form">
          <label>Model
            <select value={chosenModel} onChange={(e) => { setChosenModel(e.target.value); setSelectedModel?.(e.target.value) }}>
              {models.map((m) => <option key={m.id} value={m.name}>{m.name}</option>)}
            </select>
          </label>
        </div>
      </AnimatedCard>

      <AnimatedCard title="Latest canary rollout" className="span-2">
        <div className="canary-track">
          {CANARY_ORDER.map((stage) => (
            <span key={stage} className={`canary-step ${canaryByStage[stage] ? 'done' : ''}`}>
              {stage.replaceAll('_', ' ')}
            </span>
          ))}
        </div>
        <p className="muted" style={{ marginTop: '0.5rem' }}>Champion -&gt; 95% traffic, candidate -&gt; 5% -&gt; 25% -&gt; 50% -&gt; 100%, each gated by a health check.</p>
      </AnimatedCard>

      <AnimatedCard title="Manual rollback">
        <div className="trigger-form">
          <label>Reason
            <input type="text" value={reason} onChange={(e) => setReason(e.target.value)} />
          </label>
          <button type="button" className="primary-btn" onClick={doRollback} disabled={rollingBack}>
            {rollingBack ? 'Rolling back…' : 'Roll back to previous production version'}
          </button>
        </div>
        <p className="muted">Restores the last archived version and archives the current champion — auditable, idempotent (this platform Sec. 27).</p>
      </AnimatedCard>

      {sla && (
        <AnimatedCard title="SLA compliance (this platform Sec. 28-29)">
          <p style={{ fontSize: '2rem', margin: 0 }}>{sla.compliance_pct}%<span className="muted" style={{ fontSize: '1rem' }}> of runs within SLA</span></p>
          <p className="muted">{sla.runs_with_violation} / {sla.total_runs} runs had at least one stage exceed its SLA threshold.</p>
        </AnimatedCard>
      )}

      <AnimatedCard title="Deployment event log" className="span-2">
        <div className="table-wrap">
          <table>
            <thead><tr><th>Stage</th><th>Status</th><th>Detail</th><th>When</th></tr></thead>
            <tbody>
              {(deployment?.events || []).map((e) => (
                <tr key={e.id}><td>{e.stage.replaceAll('_', ' ')}</td><td>{e.status}</td><td className="muted">{e.detail}</td><td className="muted">{new Date(e.created_at).toLocaleString()}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </AnimatedCard>

      <AnimatedCard title="Rollback history" className="span-2">
        <div className="table-wrap">
          <table>
            <thead><tr><th>From</th><th>To</th><th>Reason</th><th>Triggered by</th><th>When</th></tr></thead>
            <tbody>
              {(deployment?.rollbacks || []).map((r) => (
                <tr key={r.id}><td>v{r.from_version}</td><td>v{r.to_version}</td><td className="muted">{r.reason}</td><td>{r.triggered_by}</td><td className="muted">{new Date(r.created_at).toLocaleString()}</td></tr>
              ))}
            </tbody>
          </table>
          {deployment && deployment.rollbacks.length === 0 && <p className="muted">No rollbacks for this model.</p>}
        </div>
      </AnimatedCard>

      {sla && (
        <AnimatedCard title="Per-stage SLA thresholds" className="span-2">
          <div className="table-wrap">
            <table>
              <thead><tr><th>Stage</th><th>Max minutes</th></tr></thead>
              <tbody>
                {Object.entries(sla.stage_thresholds).map(([name, minutes]) => (
                  <tr key={name}><td>{name.replaceAll('_', ' ')}</td><td>{minutes}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </AnimatedCard>
      )}
    </div>
  )
}
