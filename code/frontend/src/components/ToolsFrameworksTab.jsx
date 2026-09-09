import FlowAnimation from './diagrams/FlowAnimation.jsx'

const STACK_STEPS = [
  { id: 'react', label: 'React + Vite', color: '#6366f1' },
  { id: 'nginx', label: 'nginx', color: '#94a3b8' },
  { id: 'fastapi', label: 'FastAPI', color: '#059669' },
  { id: 'torch', label: 'PyTorch', color: '#ee4c2c' },
  { id: 'sklearn', label: 'scikit-learn', color: '#7c3aed' },
  { id: 'mlflow', label: 'MLflow', color: '#0ea5e9' },
  { id: 'airflow', label: 'Airflow', color: '#f59e0b' },
  { id: 'postgres', label: 'PostgreSQL', color: '#336791' },
]

const CATEGORIES = [
  {
    name: 'Backend',
    tools: [
      { name: 'FastAPI', role: 'REST API framework', why: 'Auto-generates Swagger/OpenAPI docs directly from Pydantic type hints — matches this platform\'s "document all APIs" requirement for free.' },
      { name: 'Pydantic', role: 'Request/response validation', why: 'schemas.py\'s TriggerTrainingRequest/RollbackRequest become both runtime validation and Swagger documentation.' },
      { name: 'SQLAlchemy', role: 'ORM', why: 'Declarative models map directly onto this platform Sec. 11/49\'s recommended repository/data structure.' },
    ],
  },
  {
    name: 'ML / Training',
    tools: [
      { name: 'PyTorch', role: 'Churn classifier training', why: "this platform's deep-learning framework of choice — a small MLP trained from scratch every run, with real autograd/backprop." },
      { name: 'scikit-learn', role: 'Classification metrics', why: 'Precision/recall/F1/ROC-AUC/PR-AUC for the evaluation gate (Sec. 20, 25).' },
      { name: 'MLflow', role: 'Experiment tracking + Model Registry', why: 'Its own container — every training run is logged; passing candidates are registered and stage-transitioned (Sec. 17-19, 43-44).' },
      { name: 'NumPy', role: 'Synthetic data seeding', why: 'Deterministic seeded random generators for all 5 this platform Sec. 13 scenarios.' },
    ],
  },
  {
    name: 'Orchestration',
    tools: [
      { name: 'Apache Airflow', role: 'Retraining scheduling', why: 'A real webserver + scheduler running retraining_dag.py on a weekly cron, calling the backend\'s own training API (Sec. 9, 29, 44).' },
      { name: 'PostgreSQL 16', role: 'System of record', why: 'Every table: models, datasets, records, pipeline runs/stages, versions, evaluations, deployments, rollbacks, alerts, SLA, audit log.' },
      { name: 'Docker Compose', role: 'Orchestration', why: 'One command starts every service together, standing in for this platform\'s AWS EKS deployment target.' },
    ],
  },
  {
    name: 'Frontend',
    tools: [
      { name: 'React + Vite', role: 'Frontend framework', why: 'Fast dev server, small production bundle via nginx.' },
      { name: 'nginx', role: 'Static file server + API reverse proxy', why: 'Serves the built React bundle and proxies /api/ to the backend container.' },
    ],
  },
]

export default function ToolsFrameworksTab() {
  return (
    <div className="grid tools-frameworks">
      <section className="card span-2">
        <h2>Tools &amp; frameworks used in this project</h2>
        <p>Every tool below is actually running in this docker-compose stack — nothing here is aspirational or simulated.</p>
        <FlowAnimation steps={STACK_STEPS} caption="The full path from a trigger to a trained, evaluated, gated and deployed model" />
      </section>

      {CATEGORIES.map((cat) => (
        <section key={cat.name} className="card span-2">
          <h3>{cat.name}</h3>
          <div className="tool-grid">
            {cat.tools.map((tool) => (
              <article key={tool.name} className="tool-card card animate-in">
                <div className="tool-card-head">
                  <h4>{tool.name}</h4>
                </div>
                <p className="muted">{tool.role}</p>
                <p className="tool-why">{tool.why}</p>
              </article>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
