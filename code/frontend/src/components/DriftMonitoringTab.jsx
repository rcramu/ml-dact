import { useCallback, useEffect, useState } from 'react'
import { api } from '../api.js'
import { AnimatedCard } from './shared.jsx'

const LEVEL_CLASS = { NORMAL: 'ok', WARNING: 'warn', SIGNIFICANT: 'crit' }

export default function DriftMonitoringTab({ setError, selectedModel, setSelectedModel }) {
  const [models, setModels] = useState([])
  const [chosenModel, setChosenModel] = useState('')
  const [drift, setDrift] = useState(null)
  const [history, setHistory] = useState(null)

  useEffect(() => {
    api.models().then((rows) => {
      setModels(rows)
      const initial = selectedModel || rows[0]?.name
      if (initial) setChosenModel(initial)
    }).catch((err) => setError(err.message))
  }, [selectedModel, setError])

  const load = useCallback(() => {
    if (!chosenModel) return
    api.drift(chosenModel).then(setDrift).catch((err) => setError(err.message))
    api.driftHistory(chosenModel).then(setHistory).catch((err) => setError(err.message))
  }, [chosenModel, setError])

  useEffect(() => { load() }, [load])

  return (
    <div className="grid">
      <AnimatedCard title="Drift Monitoring (PSI / KS, paper Section 8)" className="span-2">
        <p>
          Population Stability Index (PSI) and the Kolmogorov-Smirnov statistic compare every ingested
          dataset against the model&apos;s original reference (&quot;healthy&quot;) dataset. PSI below 0.10 is
          Normal, 0.10-0.25 is Warning, and above 0.25 is Significant drift &mdash; the exact threshold
          table from Section 8 of the paper.
        </p>
        <div className="trigger-form">
          <label>Model
            <select value={chosenModel} onChange={(e) => { setChosenModel(e.target.value); setSelectedModel?.(e.target.value) }}>
              {models.map((m) => <option key={m.id} value={m.name}>{m.name}</option>)}
            </select>
          </label>
          <button type="button" className="tab ghost" onClick={load}>Refresh</button>
        </div>
      </AnimatedCard>

      {drift && (
        <AnimatedCard title="Current drift status: reference vs. latest ingested dataset" className="span-2">
          <div className={`drift-overall drift-${LEVEL_CLASS[drift.drift_level] || 'ok'}`}>
            <span className="drift-overall-label">Overall PSI</span>
            <span className="drift-overall-value">{drift.psi_overall}</span>
            <span className={`status-pill ${LEVEL_CLASS[drift.drift_level] || 'ok'}`}>{drift.drift_level}</span>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Feature</th><th>PSI</th><th>KS statistic</th><th>KS p-value</th>
                <th>Reference mean</th><th>Production mean</th><th>Level</th>
              </tr>
            </thead>
            <tbody>
              {drift.features.map((f) => (
                <tr key={f.feature}>
                  <td>{f.feature}</td>
                  <td>{f.psi}</td>
                  <td>{f.ks_statistic}</td>
                  <td>{f.ks_p_value}</td>
                  <td>{f.reference_mean}</td>
                  <td>{f.production_mean}</td>
                  <td><span className={`status-pill ${LEVEL_CLASS[f.drift_level] || 'ok'}`}>{f.drift_level}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </AnimatedCard>
      )}

      {history && (
        <AnimatedCard title="PSI trend across every ingested dataset version" className="span-2">
          <table className="data-table">
            <thead><tr><th>Scenario</th><th>Ingested at</th><th>PSI (overall)</th><th>Level</th></tr></thead>
            <tbody>
              {history.history.map((h) => (
                <tr key={h.dataset_version_id}>
                  <td>{h.scenario}</td>
                  <td>{new Date(h.created_at).toLocaleString()}</td>
                  <td>{h.psi_overall}</td>
                  <td><span className={`status-pill ${LEVEL_CLASS[h.drift_level] || 'ok'}`}>{h.drift_level}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </AnimatedCard>
      )}
    </div>
  )
}
