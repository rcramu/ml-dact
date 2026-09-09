import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { AnimatedCard } from './shared.jsx'

const TABLES = [
  { id: 'datasets', label: 'Dataset Versions', cols: ['name', 'version', 'scenario', 'rows', 'features', 'seed', 'created_at'] },
  { id: 'records', label: 'Raw Records (training data)', cols: ['split', 'age', 'tenure_days', 'monthly_charges', 'support_tickets', 'usage_score', 'service_count', 'customer_satisfaction', 'is_month_to_month', 'label'] },
  { id: 'dq', label: 'Data Quality Checks', cols: ['check_name', 'passed', 'detail'] },
  { id: 'audit', label: 'Audit Log', cols: ['actor', 'action', 'resource_type', 'resource_id', 'detail', 'created_at'] },
]

export default function IngestedDataTab({ setError }) {
  const [summary, setSummary] = useState(null)
  const [active, setActive] = useState('datasets')
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.dataSummary().then(setSummary).catch((err) => setError(err.message))
  }, [setError])

  useEffect(() => {
    setLoading(true)
    const loaders = {
      datasets: () => api.datasets(50),
      records: () => api.records(150),
      dq: () => api.dataQualityChecks(100),
      audit: () => api.auditLog(100),
    }
    loaders[active]()
      .then(setRows)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [active, setError])

  const activeTable = TABLES.find((t) => t.id === active)

  return (
    <div className="grid">
      {summary && (
        <AnimatedCard title="Ingestion summary" className="span-2">
          <div className="stat-row">
            <div className="stat-pill"><span className="stat-val">{summary.models_count}</span><span className="stat-label">Models</span></div>
            <div className="stat-pill"><span className="stat-val">{summary.dataset_versions_count}</span><span className="stat-label">Dataset versions</span></div>
            <div className="stat-pill"><span className="stat-val">{summary.raw_records_count}</span><span className="stat-label">Raw records</span></div>
            <div className="stat-pill"><span className="stat-val">{summary.model_versions_count}</span><span className="stat-label">Model versions</span></div>
            <div className="stat-pill"><span className="stat-val">{summary.pipeline_runs_count}</span><span className="stat-label">Pipeline runs</span></div>
            <div className="stat-pill"><span className="stat-val">{summary.evaluation_results_count}</span><span className="stat-label">Evaluations</span></div>
            <div className="stat-pill"><span className="stat-val">{summary.deployment_events_count}</span><span className="stat-label">Deployment events</span></div>
            <div className="stat-pill"><span className="stat-val">{summary.rollback_events_count}</span><span className="stat-label">Rollbacks</span></div>
            <div className="stat-pill"><span className="stat-val">{summary.alerts_count}</span><span className="stat-label">Alerts</span></div>
            <div className="stat-pill"><span className="stat-val">{summary.audit_logs_count}</span><span className="stat-label">Audit entries</span></div>
          </div>
        </AnimatedCard>
      )}

      <AnimatedCard title="Browse ingested tables" className="span-2">
        <div className="uc-topic-filters">
          {TABLES.map((t) => (
            <button key={t.id} type="button" className={active === t.id ? 'uc-topic active' : 'uc-topic'} onClick={() => setActive(t.id)}>{t.label}</button>
          ))}
        </div>

        {loading ? (
          <p className="muted">Loading…</p>
        ) : (
          <div className="ingest-table-wrap">
            <table className="data-table">
              <thead><tr>{activeTable.cols.map((c) => <th key={c}>{c}</th>)}</tr></thead>
              <tbody>
                {rows.map((row, i) => (
                  <tr key={i}>
                    {activeTable.cols.map((c) => (
                      <td key={c}>{typeof row[c] === 'boolean' ? String(row[c]) : (row[c] ?? '—')}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="muted glossary-count">{rows.length} rows shown (sample)</p>
          </div>
        )}
      </AnimatedCard>
    </div>
  )
}
