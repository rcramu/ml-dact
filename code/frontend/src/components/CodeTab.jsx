import { useState } from 'react'
import { useConceptInterval } from '../hooks/useConceptInterval.js'

const REPO_LAYOUT = [
  { path: 'backend/app/config.py', role: 'Pydantic settings — DB/MLflow URLs, dataset sizing, training hyperparameters, gate thresholds' },
  { path: 'backend/app/models.py', role: 'SQLAlchemy ORM — models, dataset_versions, raw_records, pipeline_runs/stages, model_versions, evaluation_results, deployment_events, rollback_events, alerts, sla_configs/violations, audit_logs' },
  { path: 'backend/app/data_generator.py', role: 'Deterministic synthetic customer-churn dataset generator for every seeded scenario' },
  { path: 'backend/app/ml/drift.py', role: 'PSI / Kolmogorov-Smirnov drift statistics (paper Section 8)' },
  { path: 'backend/app/routers/drift.py', role: 'Drift Monitoring API - reference-vs-latest and PSI-trend endpoints' },
  { path: 'backend/app/pipeline_engine.py', role: 'The 16-stage retraining DAG engine (run_pipeline) + rollback() — the heart of the app' },
  { path: 'backend/app/ml/pytorch_trainer.py', role: 'ChurnMLP — a small feed-forward network trained from scratch with real PyTorch autograd (Sec. 15)' },
  { path: 'backend/app/ml/evaluation_metrics.py', role: 'scikit-learn classification metrics (Sec. 20, 25)' },
  { path: 'backend/app/ml/gates.py', role: 'Multi-metric evaluation gate + regression math (Sec. 21-23)' },
  { path: 'backend/app/integrations/mlflow_utils.py', role: 'MLflow run logging, Model Registry registration, stage transitions (Sec. 17-19, 43-44)' },
  { path: 'backend/app/routers/', role: 'health, data, training, registry, pipeline, alerts, audit' },
  { path: 'backend/app/seed.py', role: 'Startup bootstrap — seeds 2 models, runs all 5 this platform Sec. 13 scenarios plus one rollback' },
  { path: 'airflow/dags/retraining_dag.py', role: 'Real Airflow DAG scheduling weekly retraining by calling the backend\'s own API (Sec. 9, 29)' },
  { path: 'frontend/', role: 'React console — Training Runs, Models & Registry, Deployment & Rollback, Alerts, Ingested Data, API Reference, Knowledge Base' },
]

const FLOWS = [
  {
    name: 'Startup bootstrap',
    steps: [
      'FastAPI lifespan handler calls seed.bootstrap() on a fresh database',
      'Seeds the flagship churn-predictor model',
      'Runs churn-predictor through 5 planned pipeline runs: healthy (schedule), volume_anomaly (data_availability), feature_drift (drift), label_imbalance (schedule), regression (performance)',
      'Simulates a production regression and calls rollback() to restore the healthy champion',
      'Runs one more healthy training run so the fleet ends in a clean promoted state',
      'Runs churn-predictor through a single healthy training run',
    ],
  },
  {
    name: 'POST /api/v1/models/{model}/training (the 16-stage DAG)',
    steps: [
      'check_trigger records the trigger type/detail; a fresh dataset_version + raw_records are generated for the chosen scenario',
      'validate_dataset runs 5 data-quality checks; class_balance failing raises a non-blocking DATA_QUALITY_WARNING alert',
      'check_volume_anomaly compares actual vs. expected row count — a failure here BLOCKS the run immediately, skipping every later stage',
      'prepare_dataset / feature_engineering split and standardize the features',
      'train_model trains a real PyTorch ChurnMLP on the training split',
      'log_mlflow logs params + metrics as an MLflow run',
      'evaluate_model computes val/test classification metrics; compare_champion loads the current champion\'s metrics',
      'evaluation_gate applies the multi-metric gate — a FAIL rejects the candidate and stops here (REJECTED / MODEL_NOT_PROMOTED)',
      'register_model registers the passing candidate in the MLflow Model Registry',
      'deploy_stage -> post_deployment_test -> production_gate -> deploy_production progressively canary-deploys and promotes the candidate, archiving the old champion',
      'publish_metrics finalizes the run status and records any SLA violations',
    ],
  },
  {
    name: 'POST /api/v1/models/{model}/rollback',
    steps: [
      'Looks up the current champion and the most recent archived version for that model',
      'Flips the champion to stage="rolled_back", is_champion=False',
      'Promotes the previous archived version back to production/is_champion=True',
      'Logs a RollbackEvent, an AuditLog entry, and a CRITICAL PagerDuty-channel Alert',
      'Transitions both versions\' MLflow Model Registry stage accordingly',
    ],
  },
]

function FlowSteps({ title, steps }) {
  const [active, setActive] = useState(0)
  useConceptInterval(() => setActive((p) => (p + 1) % steps.length), 2800, [steps.length])
  const current = steps[active]

  return (
    <div className="concept-diagram code-flow">
      <div className="concept-diagram-head">
        <span className="concept-label">{title}</span>
        <span className="concept-step-counter">Step {active + 1}/{steps.length}</span>
      </div>
      <ol className="code-flow-list">
        {steps.map((step, index) => (
          <li key={step} className={`code-flow-step ${index === active ? 'active' : ''}`}>
            <span className="code-flow-num">{index + 1}</span>
            <p>{step}</p>
          </li>
        ))}
      </ol>
      {current && (
        <div className="concept-callout">
          <strong>Step {active + 1}</strong>
          <p>{current}</p>
        </div>
      )}
    </div>
  )
}

export default function CodeTab() {
  return (
    <div className="grid">
      <section className="card span-2">
        <h2>Explain the code</h2>
        <p className="muted">Repo layout and the three key flows behind this app's Training Runs, Models &amp; Registry, and Deployment &amp; Rollback tabs.</p>
      </section>

      <section className="card span-2">
        <h3>Repository layout</h3>
        <ul className="repo-tree">
          {REPO_LAYOUT.map((r) => (
            <li key={r.path}><code>{r.path}</code><span>{r.role}</span></li>
          ))}
        </ul>
      </section>

      {FLOWS.map((flow) => (
        <section key={flow.name} className="card span-2">
          <h3>{flow.name}</h3>
          <FlowSteps title={flow.name} steps={flow.steps} />
        </section>
      ))}
    </div>
  )
}
