import { useCallback, useEffect, useState } from 'react'
import { api } from '../api.js'
import { stackConfig } from '../config.js'
import { AnimatedCard } from './shared.jsx'

const STAGE_CLASS = { production: 'ok', candidate: 'planned', archived: 'warn', rejected: 'bad', rolled_back: 'bad' }
function StagePill({ stage }) {
  return <span className={`severity-badge severity-${STAGE_CLASS[stage] || 'ok'}`}>{stage}</span>
}

function ModelVersions({ model, onBack, setError }) {
  const [versions, setVersions] = useState(null)

  useEffect(() => {
    api.versions(model).then(setVersions).catch((err) => setError(err.message))
  }, [model, setError])

  if (!versions) return <p className="muted">Loading versions…</p>
  const champion = versions.find((v) => v.is_champion)

  return (
    <div className="grid">
      <section className="card span-2">
        <button type="button" className="ghost-btn" onClick={onBack}>&larr; Back to models</button>
        <h2>{model} <span className="muted">version lineage</span></h2>
      </section>

      {champion && (
        <AnimatedCard title="Current champion" className="span-2">
          <div className="about-pills">
            <span className="about-pill">v{champion.version}</span>
            <span className="about-pill">{champion.architecture}</span>
            <span className="about-pill">F1 {champion.test_f1.toFixed(3)}</span>
            <span className="about-pill">precision {champion.precision.toFixed(3)}</span>
            <span className="about-pill">recall {champion.recall.toFixed(3)}</span>
            <span className="about-pill">commit {champion.git_commit}</span>
          </div>
        </AnimatedCard>
      )}

      <AnimatedCard title="All versions" className="span-2">
        <div className="table-wrap">
          <table>
            <thead><tr><th>Version</th><th>Stage</th><th>F1 (train/val/test)</th><th>Precision</th><th>Recall</th><th>ROC-AUC</th><th>MLflow run</th><th>Promoted</th></tr></thead>
            <tbody>
              {versions.map((v) => (
                <tr key={v.id}>
                  <td>v{v.version}</td>
                  <td><StagePill stage={v.stage} /></td>
                  <td>{v.train_f1.toFixed(3)} / {v.val_f1.toFixed(3)} / {v.test_f1.toFixed(3)}</td>
                  <td>{v.precision.toFixed(3)}</td>
                  <td>{v.recall.toFixed(3)}</td>
                  <td>{v.roc_auc.toFixed(3)}</td>
                  <td>{v.mlflow_run_id ? <a href={`${stackConfig.mlflowUrl}/#/experiments/0/runs/${v.mlflow_run_id}`} target="_blank" rel="noreferrer">{v.mlflow_run_id.slice(0, 8)}</a> : '—'}</td>
                  <td className="muted">{v.promoted_at ? new Date(v.promoted_at).toLocaleString() : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </AnimatedCard>
    </div>
  )
}

export default function ModelsRegistryTab({ setError, selectedModel, setSelectedModel }) {
  const [models, setModels] = useState(null)

  const load = useCallback(() => {
    api.models().then(setModels).catch((err) => setError(err.message))
  }, [setError])

  useEffect(() => { load() }, [load])

  if (selectedModel) {
    return <ModelVersions model={selectedModel} onBack={() => { setSelectedModel(null); load() }} setError={setError} />
  }

  if (!models) return <p className="muted">Loading models…</p>

  return (
    <div className="grid">
      <AnimatedCard title="Models & Registry" className="span-2">
        <p>The MLflow Model Registry lifecycle (this platform Sec. 18): Candidate -&gt; Staging -&gt; Production -&gt; Archived. Only one version per model is ever the <strong>champion</strong> (currently serving production traffic).</p>
        <div className="stat-row">
          <div className="stat-pill"><span className="stat-val">{models.length}</span><span className="stat-label">Models</span></div>
          <div className="stat-pill"><span className="stat-val">{models.reduce((s, m) => s + m.version_count, 0)}</span><span className="stat-label">Total versions</span></div>
          <div className="stat-pill"><span className="stat-val">{models.reduce((s, m) => s + m.run_count, 0)}</span><span className="stat-label">Training runs</span></div>
        </div>
      </AnimatedCard>

      <AnimatedCard title="Fleet" className="span-2">
        <div className="table-wrap">
          <table>
            <thead><tr><th>Model</th><th>Task</th><th>Owner</th><th>Champion</th><th>Champion F1</th><th>Versions</th><th>Runs</th></tr></thead>
            <tbody>
              {models.map((m) => (
                <tr key={m.id} className="clickable-row" onClick={() => setSelectedModel(m.name)}>
                  <td>{m.name}</td>
                  <td>{m.task_type}</td>
                  <td>{m.owner_team}</td>
                  <td>{m.champion ? `v${m.champion.version}` : '— none yet —'}</td>
                  <td>{m.champion ? m.champion.test_f1.toFixed(3) : '—'}</td>
                  <td>{m.version_count}</td>
                  <td>{m.run_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted glossary-count">Click any row to see its full version lineage.</p>
      </AnimatedCard>
    </div>
  )
}
