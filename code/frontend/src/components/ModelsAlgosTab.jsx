import FlowAnimation from './diagrams/FlowAnimation.jsx'

const PIPELINE_STEPS = [
  { id: 'train', label: 'Train candidate', color: '#ee4c2c' },
  { id: 'eval', label: 'Evaluate vs. champion', color: '#f59e0b' },
  { id: 'gate', label: 'Evaluation gate', color: '#7c3aed' },
  { id: 'decide', label: 'Promote / reject', color: '#059669' },
]

const FORMULA_SECTIONS = [
  {
    id: 'pytorch_model',
    title: 'PyTorch churn classifier',
    formula:
`x  = [monthly_charges, support_tickets, customer_satisfaction, tenure_days,
      service_count, is_month_to_month, usage_score, late_payments]  (8-dim, standardized)

h1 = ReLU(W1.x + b1)     (16 units)
h2 = ReLU(W2.h1 + b2)    (8 units)
logit = W3.h2 + b3       (1 unit)
p(churn) = sigmoid(logit)

loss = BCEWithLogitsLoss(logit, y)   optimizer = Adam(lr=0.01)`,
    algorithm: 'A small feed-forward MLP trained from scratch every run — real PyTorch autograd + backprop, not a pretrained model.',
    metrics: ['final_train_loss, train/val/test F1, accuracy, precision, recall, ROC-AUC, PR-AUC'],
  },
  {
    id: 'classification_metrics',
    title: 'Classification metrics (this platform Sec. 20, 25)',
    formula:
`precision = TP / (TP + FP)
recall    = TP / (TP + FN)
F1        = 2 * precision * recall / (precision + recall)
ROC-AUC   = area under the ROC curve
PR-AUC    = area under the precision-recall curve (average precision)`,
    algorithm: 'Computed via scikit-learn on the held-out validation and test splits after every training run.',
    metrics: ['accuracy, precision, recall, f1, roc_auc, pr_auc'],
  },
  {
    id: 'evaluation_gate',
    title: 'Evaluation gate (this platform Sec. 21, 23)',
    formula:
`PASS  if  candidate.f1        >= minimum_f1        (0.70)
      AND candidate.recall    >= minimum_recall    (0.60)
      AND candidate.precision >= minimum_precision (0.60)
      AND regression_pct      <= max_regression_pct (10%)   [only if a champion exists]
FAIL  otherwise`,
    algorithm: 'A multi-metric gate — never relies on a single number. All conditions must hold simultaneously.',
    metrics: ['gate_result ∈ {PASS, FAIL}, reasons (human-readable explanation of every failed condition)'],
  },
  {
    id: 'regression_gate',
    title: 'Regression gate (this platform Sec. 22)',
    formula:
`regression_pct = (champion.f1 - candidate.f1) / champion.f1 * 100

Example:
  champion F1 = 0.920, candidate F1 = 0.910
  regression  = (0.920 - 0.910) / 0.920 = 1.09%  -> within a 3% budget -> PASS

  champion F1 = 0.920, candidate F1 = 0.880
  regression  = (0.920 - 0.880) / 0.920 = 4.35%  -> exceeds 3% budget -> FAIL`,
    algorithm: 'Regression is measured as a PERCENTAGE of the champion\'s score, so the same threshold is meaningful across models of different baseline difficulty.',
    metrics: ['regression_pct (nullable — null when there is no champion yet)'],
  },
  {
    id: 'data_volume_check',
    title: 'Data volume anomaly check (this platform Sec. 30)',
    formula:
`ratio = actual_rows / expected_rows

TRAINING_BLOCKED  if  ratio < (1 - tolerance)  or  ratio > (1 + tolerance)
TRAINING_ALLOWED  otherwise                          (default tolerance = 20%)`,
    algorithm: 'Runs BEFORE any training compute is spent — protects against training on a broken or incomplete data pull.',
    metrics: ['expected, actual, ratio, tolerance'],
  },
  {
    id: 'sla_formula',
    title: 'Pipeline SLA monitoring (this platform Sec. 28-29)',
    formula:
`violation  if  stage.actual_minutes > stage.max_minutes

compliance_pct = 100 * (1 - runs_with_any_violation / total_runs)`,
    algorithm: 'Every one of the 16 DAG stages has its own configurable maximum-duration budget; compliance is tracked fleet-wide.',
    metrics: ['stage_thresholds (per stage), violations, compliance_pct'],
  },
  {
    id: 'canary_math',
    title: 'Canary traffic split (this platform Sec. 25)',
    formula:
`Champion -> 95%     Candidate -> 5%
Champion -> 75%     Candidate -> 25%
Champion -> 50%     Candidate -> 50%
Champion -> 0%      Candidate -> 100%  (fully promoted)

Each step requires a passing health check before advancing.`,
    algorithm: 'Progressive traffic shifting limits the blast radius of any problem the offline evaluation gate missed.',
    metrics: ['canary stage sequence: stage -> smoke_test -> canary_5 -> canary_25 -> canary_50 -> canary_100 -> production'],
  },
];

export default function ModelsAlgosTab() {
  return (
    <div className="grid">
      <section className="card span-2">
        <h2>Formulas &amp; algorithms</h2>
        <p className="muted">Every promotion/rejection/rollback decision this platform makes traces back to one of the formulas below.</p>
        <FlowAnimation steps={PIPELINE_STEPS} caption="Train -> evaluate vs. champion -> evaluation gate -> promote or reject (this platform Sec. 15-23)" />
      </section>

      <section className="card span-2">
        <div className="formula-grid">
          {FORMULA_SECTIONS.map((section) => (
            <article key={section.id} className="formula-card card animate-in">
              <h3>{section.title}</h3>
              <pre className="code-block formula-math">{section.formula}</pre>
              <p>{section.algorithm}</p>
              {section.metrics && (
                <p className="muted"><strong>Tracked as:</strong> {section.metrics.join('; ')}</p>
              )}
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}
