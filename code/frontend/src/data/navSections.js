/** Drift-Aware Continuous Training Platform — sidebar navigation sections */

export const MAIN_NAV = [
  { id: 'drift', label: 'Drift Monitoring', description: 'PSI / KS drift statistics vs. the reference baseline (paper Section 8)' },
  { id: 'training', label: 'Training Runs', description: 'Trigger retraining, watch the 16-stage DAG, browse history' },
  { id: 'models', label: 'Models & Registry', description: 'Champion vs. challenger, version lineage, MLflow Registry' },
  { id: 'deployment', label: 'Deployment & Rollback', description: 'Canary rollout stages, automatic rollback, SLA compliance' },
  { id: 'alerts', label: 'Alerts', description: 'Slack/PagerDuty-style notifications across the whole pipeline' },
  { id: 'ingested-data', label: 'Ingested Data', description: 'Seeded datasets, raw training records, audit trail' },
]

export const PLATFORM_NAV = [
  { id: 'api-reference', label: 'API Reference', description: 'Endpoint catalog · Swagger · ReDoc' },
]

// Order matters — matches the user's requested Knowledge Base layout exactly;
// "Check My Understanding" must stay last.
export const KB_NAV = [
  { id: 'kb-about', label: 'About this Project', kbSection: 'about', description: 'Drift-Aware Continuous Training Platform vision & scope' },
  { id: 'kb-concepts', label: 'Concept Preview', kbSection: 'concepts', description: 'Illustrated concepts · flashcards' },
  { id: 'kb-glossary', label: 'Term Glossary', kbSection: 'glossary', description: 'Searchable term definitions' },
  { id: 'kb-models', label: 'Formulas & Algorithms', kbSection: 'models', description: 'Gates, regression math, PyTorch model, SLA formulas' },
  { id: 'kb-architecture', label: 'Architecture', kbSection: 'architecture', description: 'Full DAG · roadmap' },
  { id: 'kb-code', label: 'Explain the Code', kbSection: 'code', description: 'Repo layout · pipeline & rollback flows' },
  { id: 'kb-tools', label: 'Tools & Frameworks', kbSection: 'tools', description: 'FastAPI, PyTorch, MLflow, Airflow, PostgreSQL, React' },
  { id: 'kb-check', label: 'Check My Understanding', kbSection: 'check', description: 'Self-check quiz (7+ questions per topic)' },
]

export function isKbView(view) {
  return String(view).startsWith('kb-')
}

export function kbSectionFromView(view) {
  const item = KB_NAV.find((n) => n.id === view)
  return item?.kbSection || 'about'
}

