import FlowAnimation from './diagrams/FlowAnimation.jsx'

const DAG_STEPS = [
  { id: 'trigger', label: 'Trigger', color: '#94a3b8' },
  { id: 'validate', label: 'Validate + volume check', color: '#0ea5e9' },
  { id: 'train', label: 'PyTorch training', color: '#ee4c2c' },
  { id: 'mlflow', label: 'MLflow tracking', color: '#7c3aed' },
  { id: 'gate', label: 'Evaluation gate', color: '#f59e0b' },
  { id: 'deploy', label: 'Canary deploy', color: '#059669' },
]

const CLOSED_LOOP_STEPS = [
  { id: 'prod', label: 'Production model', color: '#94a3b8' },
  { id: 'drift', label: 'Drift Detection Dashboard', color: '#0ea5e9' },
  { id: 'trigger', label: 'Training trigger', color: '#6366f1' },
  { id: 'dag', label: 'Airflow DAG', color: '#7c3aed' },
  { id: 'gate', label: 'Evaluate + gate', color: '#f59e0b' },
  { id: 'monitor', label: 'Monitor', color: '#059669' },
]

const COMPONENTS = [
  { name: 'PostgreSQL 16', role: 'models, dataset_versions, raw_records, pipeline_runs/stages, model_versions, evaluation_results, deployment_events, rollback_events, alerts, sla_configs/violations, audit_logs (this platform Sec. 11, 28, 49)' },
  { name: 'FastAPI backend', role: 'REST API, request validation (Pydantic), Swagger/OpenAPI docs, the full 16-stage pipeline engine' },
  { name: 'MLflow server', role: 'Its own container — every training run is tracked; a candidate is registered as a numbered Model Registry version only after passing the gate (Sec. 17-19)' },
  { name: 'PyTorch', role: 'Trains a fresh feed-forward MLP churn classifier from scratch on every run' },
  { name: 'scikit-learn', role: 'Classification metrics (accuracy/precision/recall/F1/ROC-AUC/PR-AUC) for the evaluation gate (Sec. 20, 25)' },
  { name: 'Apache Airflow', role: 'Real webserver + scheduler orchestrating the weekly retraining_dag (Sec. 9, 29, 44)' },
  { name: 'React + Vite UI', role: 'Training Runs, Models & Registry, Deployment & Rollback, Alerts, Ingested Data, API Reference, Knowledge Base' },
]

const NFRS = [
  { name: 'Reproducibility', target: 'Fixed, SHA-256-derived seed for every scenario generator', measure: 'Same seed -> same synthetic dataset, same trained model, same gate decision' },
  { name: 'Safety', target: 'A candidate must never reach production without passing the gate (Sec. 21)', measure: 'register_model/deploy_* stages are only reached after gate_result == PASS' },
  { name: 'Auditability', target: 'Every promote/reject/rollback traceable to who/what/when/why (Sec. 48)', measure: 'AuditLog row written at every decision point' },
  { name: 'Recoverability', target: 'Rollback initiation should be fast and always possible (Sec. 27)', measure: 'The previous production version is archived, never deleted, until it is itself replaced' },
]

const ROADMAP_PHASES = [
  { phase: 'This app', detail: 'Real triggers, real PyTorch training, real MLflow tracking + Registry, multi-metric evaluation gate, canary deployment simulation, automatic rollback, per-stage SLA monitoring, full audit trail — all via Docker Compose' },
  { phase: 'Near-term roadmap', detail: 'Statistical significance testing (bootstrap CIs, McNemar\'s test) before promotion (Sec. 24); real Slack/PagerDuty webhook delivery instead of logged Alert rows (Sec. 37-38)' },
  { phase: 'Production roadmap', detail: 'AWS EKS deployment with dedicated GPU node groups for PyTorch training (Sec. 50-51); S3/Aurora PostgreSQL; IAM/KMS/Secrets Manager; CI/CD pipeline with security scanning (Sec. 41-42, 47)' },
  { phase: 'Scale', detail: 'this platform\'s fleet-scale numbers (12.5M-row datasets, 1,000+ models) — this MVP intentionally runs at demo scale (~900 rows, 2 models) to stay fast on a laptop' },
]

export default function ArchitectureTab() {
  return (
    <div className="grid">
      <section className="card span-2">
        <h2>The 16-stage retraining DAG</h2>
        <p>Every trigger (drift, performance, schedule, data availability, or manual) starts the same DAG: validate -&gt; train -&gt; track -&gt; evaluate -&gt; gate -&gt; canary deploy -&gt; publish metrics (this platform Sec. 9-10).</p>
        <FlowAnimation steps={DAG_STEPS} caption="check_trigger -> ... -> evaluation_gate -> register_model -> canary -> deploy_production -> publish_metrics" />
      </section>

      <section className="card span-2">
        <h2>The closed loop (this platform Sec. 53)</h2>
        <FlowAnimation steps={CLOSED_LOOP_STEPS} caption="Production model -> drift detected -> training triggered -> Airflow DAG -> evaluate/gate -> deploy or reject -> monitor -> (loop)" />
      </section>

      <section className="card">
        <h2>Components</h2>
        <ul className="arch-list">
          {COMPONENTS.map((c) => (
            <li key={c.name}><strong>{c.name}</strong> — {c.role}</li>
          ))}
        </ul>
      </section>

      <section className="card">
        <h2>Non-functional requirements</h2>
        <table className="data-table">
          <thead><tr><th>NFR</th><th>Target</th><th>Measure</th></tr></thead>
          <tbody>
            {NFRS.map((row) => (
              <tr key={row.name}>
                <td>{row.name}</td>
                <td>{row.target}</td>
                <td className="muted">{row.measure}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="card span-2">
        <h2>Roadmap (this platform Sec. 46-56)</h2>
        <ol className="about-steps">
          {ROADMAP_PHASES.map((p) => (
            <li key={p.phase}><strong>{p.phase}:</strong> {p.detail}</li>
          ))}
        </ol>
      </section>
    </div>
  )
}
