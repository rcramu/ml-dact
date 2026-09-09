import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { stackConfig } from '../config.js'
import { AnimatedCard } from './shared.jsx'
import FlowAnimation from './diagrams/FlowAnimation.jsx'

const API_FLOW_STEPS = [
  { id: 'req', label: 'Request', color: '#6366f1' },
  { id: 'fastapi', label: 'FastAPI', color: '#059669' },
  { id: 'pg', label: 'PostgreSQL', color: '#0ea5e9' },
  { id: 'resp', label: 'JSON response', color: '#f59e0b' },
]

export default function ApiReferenceTab({ setError }) {
  const [catalog, setCatalog] = useState(null)

  useEffect(() => {
    api.catalog().then(setCatalog).catch((err) => setError(err.message))
  }, [setError])

  if (!catalog) return <p className="muted">Loading API catalog…</p>

  return (
    <div className="grid">
      <AnimatedCard title={`${catalog.service} v${catalog.version}`} className="span-2">
        <p>{catalog.description}</p>
        <FlowAnimation steps={API_FLOW_STEPS} caption="Every endpoint below is documented automatically via FastAPI's OpenAPI schema." />
        <div className="doc-links">
          <a href={`${stackConfig.apiUrl}${catalog.swagger_url}`} target="_blank" rel="noreferrer">Swagger UI</a>
          <a href={`${stackConfig.apiUrl}${catalog.redoc_url}`} target="_blank" rel="noreferrer">ReDoc</a>
          <a href={`${stackConfig.apiUrl}${catalog.openapi_url}`} target="_blank" rel="noreferrer">OpenAPI JSON</a>
          <a href={stackConfig.mlflowUrl} target="_blank" rel="noreferrer">MLflow tracking UI</a>
          <a href={stackConfig.airflowUrl} target="_blank" rel="noreferrer">Airflow</a>
        </div>
      </AnimatedCard>


      {catalog.groups.map((group) => (
        <AnimatedCard key={group.tag} title={group.tag} className="span-2">
          <p className="muted">{group.description}</p>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Method</th><th>Path</th><th>Description</th></tr></thead>
              <tbody>
                {group.endpoints.map((ep) => (
                  <tr key={`${ep.method}-${ep.path}`}>
                    <td><span className={`method-badge ${ep.method.toLowerCase()}`}>{ep.method}</span></td>
                    <td><code>{ep.path}</code></td>
                    <td className="muted">{ep.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </AnimatedCard>
      ))}
    </div>
  )
}
