/** Drift-Aware Continuous Training Platform glossary */

export const GLOSSARY_TOPICS = [
  { id: 'pipeline', label: 'Pipeline & Triggers' },
  { id: 'evaluation', label: 'Evaluation & Gates' },
  { id: 'deployment', label: 'Deployment & Rollback' },
  { id: 'platform', label: 'Platform' },
]

export function glossaryTermsForTopic(topicId) {
  if (topicId === 'all') return Object.keys(GLOSSARY)
  return Object.entries(GLOSSARY)
    .filter(([, e]) => e.topic === topicId)
    .map(([id]) => id)
}

export const GLOSSARY = {
  continuous_training: {
    term: 'Continuous Training (CT)',
    topic: 'pipeline',
    definition: 'Automatically retraining a production model whenever predefined conditions occur (drift, performance dip, schedule, new data, manual request).',
    inThisStack: 'The whole app — app/pipeline_engine.py\'s run_pipeline() implements the closed loop end to end.',
  },
  drift_trigger: {
    term: 'Drift trigger',
    topic: 'pipeline',
    definition: 'Retraining initiated because a companion drift-detection system observed a meaningful shift in feature or prediction distributions.',
    inThisStack: 'Seeded as the "feature_drift" scenario — customer_satisfaction and service_count distributions shift.',
  },
  volume_anomaly: {
    term: 'Data volume anomaly',
    topic: 'pipeline',
    definition: 'The actual row count of a training dataset falls far outside the expected range — a signal that something upstream is broken, not just "less data than usual".',
    inThisStack: 'app/pipeline_engine.py\'s check_volume_anomaly stage compares actual rows to CTP_EXPECTED_VOLUME +/- 20%.',
  },
  dag: {
    term: 'DAG (Directed Acyclic Graph)',
    topic: 'pipeline',
    definition: 'A workflow made of steps with dependencies but no cycles — the standard shape for a data/ML pipeline.',
    inThisStack: 'The 16-stage retraining DAG defined in app/pipeline_engine.py\'s DAG_STAGES, orchestrated by Airflow.',
  },
  champion_challenger: {
    term: 'Champion / Challenger',
    topic: 'evaluation',
    definition: 'The champion is the model version currently serving production traffic; a challenger is a newly trained candidate competing to replace it.',
    inThisStack: 'ModelVersion.is_champion flags the current champion per model; every new candidate is compared against it.',
  },
  evaluation_gate: {
    term: 'Evaluation gate',
    topic: 'evaluation',
    definition: 'A mandatory set of pass/fail conditions (minimum metrics + maximum regression) a candidate model must satisfy before it can be promoted.',
    inThisStack: 'app/ml/gates.py\'s evaluation_gate() — see the Formulas & Algorithms tab for the exact math.',
  },
  regression_pct: {
    term: 'Regression percentage',
    topic: 'evaluation',
    definition: 'How much worse a candidate\'s metric is than the champion\'s, expressed as a percentage of the champion\'s value.',
    inThisStack: 'Computed in evaluation_gate(); a candidate is rejected once this exceeds CTP_MAX_REGRESSION_PCT (default 3%).',
  },
  f1_score: {
    term: 'F1 score',
    topic: 'evaluation',
    definition: 'The harmonic mean of precision and recall — a single number balancing both false positives and false negatives.',
    inThisStack: 'The primary gating metric computed by app/ml/evaluation_metrics.py\'s classification_metrics().',
  },
  class_imbalance: {
    term: 'Class imbalance',
    topic: 'evaluation',
    definition: 'A dataset where one label is far more common than another (e.g. 98% retained vs. 2% churned), which can make naively-trained models collapse to always predicting the majority class.',
    inThisStack: 'Seeded as the "label_imbalance" scenario — the resulting candidate typically fails the minimum-recall gate.',
  },
  model_registry: {
    term: 'MLflow Model Registry',
    topic: 'platform',
    definition: 'MLflow\'s catalog of named, versioned models with lifecycle stages (Candidate/Staging/Production/Archived).',
    inThisStack: 'app/integrations/mlflow_utils.py\'s register_run_as_model_version() and transition_stage().',
  },
  canary_deployment: {
    term: 'Canary deployment',
    topic: 'deployment',
    definition: 'Gradually shifting production traffic to a new version (e.g. 5% -> 25% -> 50% -> 100%) instead of an instant full cutover, so problems are caught while impact is still small.',
    inThisStack: 'app/pipeline_engine.py\'s CANARY_STAGES and _deploy_and_promote().',
  },
  automatic_rollback: {
    term: 'Automatic rollback',
    topic: 'deployment',
    definition: 'Restoring the previous production model automatically the moment a post-deployment regression is detected, without waiting for manual investigation.',
    inThisStack: 'app/pipeline_engine.py\'s rollback() function; seeded once at startup and also triggerable manually from the UI.',
  },
  sla_violation: {
    term: 'SLA violation',
    topic: 'deployment',
    definition: 'A pipeline stage that took longer than its configured maximum allowed duration.',
    inThisStack: 'app/models.py\'s SlaViolation table, populated whenever a stage\'s simulated_minutes exceeds SLA_DEFAULTS.',
  },
  audit_trail: {
    term: 'Audit trail / governance log',
    topic: 'platform',
    definition: 'An immutable, chronological record of who did what, when, and why — required for regulated or high-stakes automated decisions.',
    inThisStack: 'app/models.py\'s AuditLog table — every promote/reject/rollback/block decision is recorded.',
  },
  eks_roadmap: {
    term: 'AWS EKS (roadmap only)',
    topic: 'platform',
    definition: 'AWS\'s managed Kubernetes service — the PRD\'s intended production runtime for GPU training jobs and the pipeline itself.',
    inThisStack: 'Documented, not deployed — this MVP runs everything via Docker Compose on a single host instead.',
  },
}
