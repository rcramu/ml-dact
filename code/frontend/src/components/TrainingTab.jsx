import { useCallback, useEffect, useState } from 'react'
import { api } from '../api.js'
import { stackConfig } from '../config.js'
import { AnimatedCard } from './shared.jsx'
import FlowAnimation from './diagrams/FlowAnimation.jsx'

const STATE_CLASS = { SUCCESS: 'ok', FAILED: 'bad', BLOCKED: 'bad', REJECTED: 'warn', RUNNING: 'ok' }
function StatusPill({ status }) {
  return <span className={`severity-badge severity-${STATE_CLASS[status] || 'ok'}`}>{status}</span>
}

const TRIGGER_TYPES = ['manual', 'drift', 'performance', 'schedule', 'data_availability']

const DAG_FLOW = [
  { id: 'trigger', label: 'Trigger', color: '#94a3b8' },
  { id: 'validate', label: 'Validate data', color: '#0ea5e9' },
  { id: 'train', label: 'Train (PyTorch)', color: '#ee4c2c' },
  { id: 'mlflow', label: 'MLflow', color: '#7c3aed' },
  { id: 'gate', label: 'Evaluation gate', color: '#f59e0b' },
  { id: 'deploy', label: 'Canary -> Production', color: '#059669' },
]

function StageStepper({ stages }) {
  return (
    <div className="stage-stepper">
      {stages.map((s) => (
        <div key={s.stage_name} className={`stage-step ${s.status}`}>
          <span className="stage-step-index">{s.stage_order + 1}</span>
          <span className="stage-step-name">{s.stage_name.replaceAll('_', ' ')}</span>
          {s.simulated_minutes > 0 && <span className="stage-step-minutes">{s.simulated_minutes}m</span>}
          <span className="stage-step-status">{s.status}</span>
        </div>
      ))}
    </div>
  )
}

function RunDetail({ model, runId, onBack, setError }) {
  const [run, setRun] = useState(null)
  const [evaluation, setEvaluation] = useState(null)

  const load = useCallback(() => {
    api.trainingStatus(model, runId).then(setRun).catch((err) => setError(err.message))
    api.evaluationDetail(model, runId).then(setEvaluation).catch(() => setEvaluation(null))
  }, [model, runId, setError])

  useEffect(() => { load() }, [load])

  if (!run) return <p className="muted">Loading training run…</p>

  return (
    <div className="grid">
      <section className="card span-2">
        <button type="button" className="ghost-btn" onClick={onBack}>&larr; Back to training</button>
        <h2>{model} <StatusPill status={run.status} /></h2>
        <p className="muted">Trigger: <strong>{run.trigger_type}</strong> — {run.trigger_detail}</p>
        {run.outcome && <p><strong>Outcome:</strong> {run.outcome}</p>}
      </section>

      <AnimatedCard title="16-stage retraining DAG (this platform Sec. 10)" className="span-2">
        <StageStepper stages={run.stages} />
      </AnimatedCard>

      {evaluation && (
        <AnimatedCard title="Evaluation gate result" className="span-2">
          <div className="compare-grid">
            <div className="compare-col">
              <h4>Champion</h4>
              <div className="compare-value">{evaluation.champion_metrics.f1 != null ? evaluation.champion_metrics.f1.toFixed(3) : '—'}</div>
              <p className="muted">F1</p>
            </div>
            <span className="compare-vs">VS</span>
            <div className="compare-col">
              <h4>Candidate</h4>
              <div className="compare-value">{evaluation.candidate_metrics.f1.toFixed(3)}</div>
              <p className="muted">F1</p>
            </div>
          </div>
          <p style={{ marginTop: '0.75rem' }}>
            <strong>Gate result: </strong><StatusPill status={evaluation.gate_result === 'PASS' ? 'SUCCESS' : 'FAILED'} />
            {evaluation.regression_pct != null && <span className="muted"> · regression {evaluation.regression_pct}%</span>}
          </p>
          <p className="muted">{evaluation.reasons}</p>
        </AnimatedCard>
      )}
    </div>
  )
}

export default function TrainingTab({ setError, selectedModel, setSelectedModel, onOpenModel }) {
  const [models, setModels] = useState([])
  const [chosenModel, setChosenModel] = useState('')
  const [triggerType, setTriggerType] = useState('manual')
  const [scenario, setScenario] = useState('healthy')
  const [triggerDetail, setTriggerDetail] = useState('')
  const [scenarios, setScenarios] = useState([])
  const [running, setRunning] = useState(false)
  const [history, setHistory] = useState(null)
  const [openRunId, setOpenRunId] = useState(null)

  const loadModels = useCallback(() => {
    api.models().then((rows) => {
      setModels(rows)
      if (!chosenModel && rows.length) setChosenModel(rows[0].name)
    }).catch((err) => setError(err.message))
  }, [chosenModel, setError])

  useEffect(() => { loadModels() }, [loadModels])
  useEffect(() => {
    api.seedScenarios().then((d) => setScenarios(d.scenarios)).catch((err) => setError(err.message))
  }, [setError])

  const loadHistory = useCallback(() => {
    if (!chosenModel) return
    api.trainingHistory(chosenModel, 50).then(setHistory).catch((err) => setError(err.message))
  }, [chosenModel, setError])

  useEffect(() => { loadHistory() }, [loadHistory])

  if (selectedModel && openRunId) {
    return <RunDetail model={selectedModel} runId={openRunId} onBack={() => { setOpenRunId(null); loadHistory() }} setError={setError} />
  }

  const trigger = async () => {
    if (!chosenModel) return
    setRunning(true)
    try {
      const run = await api.triggerTraining(chosenModel, { trigger_type: triggerType, scenario, trigger_detail: triggerDetail })
      setSelectedModel(chosenModel)
      setOpenRunId(run.id)
      loadModels()
    } catch (err) { setError(err.message) } finally { setRunning(false) }
  }

  return (
    <div className="grid">
      <AnimatedCard title="Drift-Aware Continuous Training Platform" className="span-2">
        <p>Every training run walks the same 16-stage DAG (this platform Sec. 10): validate data, check volume, train a real PyTorch model, log to MLflow, evaluate against the current champion, gate the promotion decision, then canary-deploy to production.</p>
        <FlowAnimation steps={DAG_FLOW} caption="check_trigger -> validate_dataset -> ... -> evaluation_gate -> register_model -> canary -> deploy_production -> publish_metrics" />
      </AnimatedCard>

      <AnimatedCard title="Trigger a training run" className="span-2">
        <div className="trigger-form">
          <label>Model
            <select value={chosenModel} onChange={(e) => setChosenModel(e.target.value)}>
              {models.map((m) => <option key={m.id} value={m.name}>{m.name}</option>)}
            </select>
          </label>
          <label>Trigger type
            <select value={triggerType} onChange={(e) => setTriggerType(e.target.value)}>
              {TRIGGER_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </label>
          <label>Data scenario (this platform Sec. 13)
            <select value={scenario} onChange={(e) => setScenario(e.target.value)}>
              {scenarios.map((s) => <option key={s.id} value={s.id}>{s.id} — {s.expected_outcome}</option>)}
            </select>
          </label>
          <label>Trigger detail (optional)
            <input type="text" placeholder="e.g. PSI=0.24 on customer_satisfaction" value={triggerDetail} onChange={(e) => setTriggerDetail(e.target.value)} />
          </label>
          <button type="button" className="primary-btn" onClick={trigger} disabled={running || !chosenModel}>
            {running ? 'Running 16-stage DAG…' : 'Trigger training'}
          </button>
        </div>
        <p className="muted">Mirrors what the Airflow <code>retraining_dag</code> calls weekly — see it live at <a href={stackConfig.airflowUrl} target="_blank" rel="noreferrer">Airflow</a>.</p>
      </AnimatedCard>

      <AnimatedCard title={`Training history — ${chosenModel || '…'}`} className="span-2">
        <div className="table-wrap">
          <table>
            <thead><tr><th>Trigger</th><th>Scenario/Detail</th><th>Status</th><th>Outcome</th><th>Started</th></tr></thead>
            <tbody>
              {(history || []).map((r) => (
                <tr key={r.id} className="clickable-row" onClick={() => { setSelectedModel(chosenModel); setOpenRunId(r.id) }}>
                  <td>{r.trigger_type}</td>
                  <td className="muted">{r.trigger_detail}</td>
                  <td><StatusPill status={r.status} /></td>
                  <td>{r.outcome || '—'}</td>
                  <td className="muted">{new Date(r.started_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {history && history.length === 0 && <p className="muted">No training runs yet for this model.</p>}
        </div>
      </AnimatedCard>
    </div>
  )
}
