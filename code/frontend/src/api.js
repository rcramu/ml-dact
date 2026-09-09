const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

async function request(path, options) {
  const res = await fetch(`${API_BASE}${path}`, options)
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = data.detail
    const message = typeof detail === 'string' ? detail : JSON.stringify(detail) || res.statusText
    throw new Error(message)
  }
  return data
}

function postJson(path, body) {
  return request(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) })
}

export const api = {
  ready: () => request('/ready'),

  // Ingested Data
  dataSummary: () => request('/data/summary'),
  datasets: (limit = 50) => request(`/data/datasets?limit=${limit}`),
  records: (limit = 100, datasetVersionId, split) => request(
    `/data/records?limit=${limit}${datasetVersionId ? `&dataset_version_id=${datasetVersionId}` : ''}${split ? `&split=${split}` : ''}`,
  ),
  dataQualityChecks: (limit = 100, datasetVersionId) => request(`/data/data-quality-checks?limit=${limit}${datasetVersionId ? `&dataset_version_id=${datasetVersionId}` : ''}`),
  auditLog: (limit = 100) => request(`/data/audit-log?limit=${limit}`),
  seedScenarios: () => request('/data/seed-scenarios'),

  // Models & Registry
  models: () => request('/api/v1/models'),
  versions: (model, limit = 100) => request(`/api/v1/models/${encodeURIComponent(model)}/versions?limit=${limit}`),
  deployment: (model) => request(`/api/v1/models/${encodeURIComponent(model)}/deployment`),

  // Drift Monitoring
  drift: (model) => request(`/api/v1/models/${encodeURIComponent(model)}/drift`),
  driftHistory: (model) => request(`/api/v1/models/${encodeURIComponent(model)}/drift/history`),

  // Training
  triggerTraining: (model, body) => postJson(`/api/v1/models/${encodeURIComponent(model)}/training`, body),
  trainingStatus: (model, runId) => request(`/api/v1/models/${encodeURIComponent(model)}/training/${encodeURIComponent(runId)}`),
  trainingHistory: (model, limit = 50) => request(`/api/v1/models/${encodeURIComponent(model)}/training/history?limit=${limit}`),
  evaluationDetail: (model, runId) => request(`/api/v1/models/${encodeURIComponent(model)}/evaluation/${encodeURIComponent(runId)}`),
  rollback: (model, reason) => postJson(`/api/v1/models/${encodeURIComponent(model)}/rollback`, { reason }),

  // Pipeline / SLA
  pipelineRuns: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/pipeline/runs${qs ? `?${qs}` : ''}`)
  },
  pipelineRunDetail: (runId) => request(`/pipeline/runs/${encodeURIComponent(runId)}`),
  sla: () => request('/pipeline/sla'),

  // Alerts
  alerts: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/alerts${qs ? `?${qs}` : ''}`)
  },
  resolveAlert: (alertId) => postJson(`/alerts/${encodeURIComponent(alertId)}/resolve`),

  catalog: () => request('/docs-catalog'),
}
