/** Concept Preview — this platform Sec. 7-10, 17-27, 39-44, illustrated with a quick example each. */

export const CONCEPTS = [
  {
    id: 'retraining_triggers',
    title: 'Retraining Triggers',
    subtitle: 'What actually starts a new training run?',
    illustration: 'triggers',
    summary:
      'Retraining can be triggered by feature/prediction drift, a production-performance dip, a fixed ' +
      'schedule, new labeled data becoming available, a data-volume anomaly (which should BLOCK training, ' +
      'not start it), or a manual request. Multiple simultaneous triggers are deduplicated by priority.',
    example: {
      title: 'Try it in this app',
      steps: [
        'Open "Training Runs" and look at churn-predictor\'s history — 5 different trigger types already ran at startup',
        'Notice the "volume_anomaly" run has status BLOCKED, not FAILED — it never reached training at all',
        'Trigger a new run yourself and pick any trigger_type + scenario combination from the dropdowns',
      ],
    },
    flashcard: {
      emoji: '⚡',
      question: 'Why must a data-volume anomaly BLOCK training instead of just training on less data?',
      takeaway: 'Training on an unexpectedly small or malformed slice of data can produce a worse model that still looks superficially fine — blocking is safer than silently degrading quality.',
      try_it: 'See app/pipeline_engine.py\'s check_volume_anomaly stage in the Explain the Code tab.',
    },
    kb_section: 'code',
  },
  {
    id: 'evaluation_gate',
    title: 'The Evaluation Gate',
    subtitle: 'Why a candidate must EARN promotion',
    illustration: 'gate',
    summary:
      'Before any candidate model reaches production, it must pass a multi-metric gate: minimum F1/precision/' +
      'recall thresholds, AND (if a champion exists) a maximum allowed regression versus that champion. ' +
      'Never rely on a single metric — a model can look fine on F1 while quietly losing recall.',
    example: {
      title: 'Worked example',
      steps: [
        'churn-predictor\'s "label_imbalance" run trains on a 98/2 class split',
        'The candidate\'s recall collapses well below the 0.75 minimum — the gate FAILS on recall alone, even if F1 looked passable',
        'Open that run\'s Evaluation Gate card in Training Runs to see the exact reasons text',
      ],
    },
    flashcard: {
      emoji: '🚦',
      question: 'Why check recall AND precision AND F1, instead of just F1?',
      takeaway: 'F1 is a single blended number — a model can hit an acceptable F1 while recall (catching real churners) or precision (not crying wolf) individually falls to an unacceptable level.',
      try_it: 'See app/ml/gates.py\'s evaluation_gate() in the Formulas & Algorithms tab.',
    },
    kb_section: 'models',
  },
  {
    id: 'regression_math',
    title: 'Regression Math',
    subtitle: 'How "3% worse" is actually computed',
    illustration: 'regression',
    summary:
      'Regression is not eyeballed — it is a precise percentage: (champion_f1 - candidate_f1) / champion_f1 ' +
      '* 100. If that number exceeds the configured maximum (3% by default), the candidate is rejected no ' +
      'matter how good it otherwise looks.',
    example: {
      title: 'Worked example',
      steps: [
        'Champion F1 = 0.920, candidate F1 = 0.910 -> regression = (0.920-0.910)/0.920 = 1.09% -> PASSES a 3% budget',
        'Champion F1 = 0.920, candidate F1 = 0.880 -> regression = 4.35% -> FAILS a 3% budget',
        'churn-predictor\'s "regression" scenario run deliberately produces the second case',
      ],
    },
    flashcard: {
      emoji: '📉',
      question: 'Why measure regression as a PERCENTAGE of the champion\'s score, not a raw point difference?',
      takeaway: 'A 0.03 drop means something very different at F1=0.95 (a 3.2% regression) than at F1=0.60 (a 5% regression) — percentage-of-champion keeps the threshold meaningful across models with different baseline difficulty.',
      try_it: 'See app/ml/gates.py\'s evaluation_gate() regression_pct calculation.',
    },
    kb_section: 'models',
  },
  {
    id: 'canary_deployment',
    title: 'Canary Deployment',
    subtitle: 'Never flip 100% of traffic at once',
    illustration: 'canary',
    summary:
      'A promoted candidate does not go straight to 100% production traffic. It progresses through staged ' +
      'canary percentages — 5%, 25%, 50%, 100% — with a health check gating each step, so a subtle problem ' +
      'only missed by the offline evaluation gate is caught before it affects every user.',
    example: {
      title: 'Try it in this app',
      steps: [
        'Open "Deployment & Rollback" and pick churn-predictor',
        'The "Latest canary rollout" track shows stage -> smoke_test -> canary_5 -> canary_25 -> canary_50 -> canary_100 -> production, all green',
        'Every stage is also a row in the Deployment event log below it, with its own timestamp',
      ],
    },
    flashcard: {
      emoji: '🐤',
      question: 'If the offline evaluation gate already passed, why still canary-deploy gradually?',
      takeaway: 'Offline evaluation uses historical test data — canary deployment is the only way to observe real, live traffic behavior before it affects 100% of users.',
      try_it: 'See app/pipeline_engine.py\'s _deploy_and_promote() in the Explain the Code tab.',
    },
    kb_section: 'code',
  },
  {
    id: 'automatic_rollback',
    title: 'Automatic Rollback',
    subtitle: 'The safety net for production regressions',
    illustration: 'rollback',
    summary:
      'If a production regression is detected AFTER deployment (e.g. by a companion Drift Detection ' +
      'Dashboard), the previous champion must be restored automatically, quickly, and auditably — the ' +
      'platform never leaves a known-bad model serving traffic while a human investigates.',
    example: {
      title: 'Try it in this app',
      steps: [
        'This app seeds one real rollback at startup: churn-predictor v2 is rolled back to v1 after a simulated production regression',
        'Open "Deployment & Rollback" to see the rollback event, its reason, and which version was restored',
        'Try the manual "Roll back to previous production version" button yourself — it is the same underlying function',
      ],
    },
    flashcard: {
      emoji: '⏮️',
      question: 'Why must rollback be idempotent (safe to trigger more than once)?',
      takeaway: 'Automated systems retry on ambiguous failures. If rollback were not idempotent, a retried rollback could roll back an already-rolled-back model a second time, corrupting the deployment state.',
      try_it: 'See app/pipeline_engine.py\'s rollback() function in the Explain the Code tab.',
    },
    kb_section: 'code',
  },
  {
    id: 'mlflow_registry',
    title: 'MLflow Tracking & the Model Registry',
    subtitle: 'Every model version, fully traceable',
    illustration: 'lineage',
    summary:
      'Every training run logs its hyperparameters, metrics and tags to MLflow. Only a run that PASSES the ' +
      'evaluation gate is additionally registered as a numbered Model Registry version and transitioned ' +
      'through Candidate -> Staging -> Production -> Archived as it is promoted or replaced.',
    example: {
      title: 'Try it in this app',
      steps: [
        'Open "Models & Registry" and click into churn-predictor',
        'Every version (including rejected ones) shows its MLflow run link — click through to see the logged params/metrics',
        'Only the promoted versions ever reach the "production" stage; rejected candidates stay "rejected" forever',
      ],
    },
    flashcard: {
      emoji: '🔗',
      question: 'Why log a rejected candidate\'s training run to MLflow at all, if it never gets promoted?',
      takeaway: 'Rejected runs are valuable evidence — they let you audit exactly why a retraining attempt failed and compare it against future attempts on the same or similar data.',
      try_it: 'See app/integrations/mlflow_utils.py in the Explain the Code tab.',
    },
    kb_section: 'architecture',
  },
  {
    id: 'sla_reliability',
    title: 'Pipeline SLA Monitoring',
    subtitle: 'The pipeline itself needs a reliability target',
    illustration: 'sla',
    summary:
      'A retraining pipeline is production infrastructure — each of its 16 stages has its own maximum-' +
      'duration SLA (e.g. training < 120 minutes). A stage that exceeds its budget is logged as an SLA ' +
      'violation, rolling up into a fleet-wide compliance percentage.',
    example: {
      title: 'Try it in this app',
      steps: [
        'Open "Deployment & Rollback" and check the "SLA compliance" card',
        'The "Per-stage SLA thresholds" table shows this platform Sec. 29\'s exact example minutes for every stage',
        'Some seeded runs deliberately simulate a slower-than-usual stage to populate real SLA violations',
      ],
    },
    flashcard: {
      emoji: '⏱️',
      question: 'Why track SLA per STAGE instead of just the whole pipeline\'s total duration?',
      takeaway: 'A single slow stage (e.g. training) can hide inside an otherwise-fast pipeline\'s total time — per-stage SLAs pinpoint exactly which part of the DAG needs attention.',
      try_it: 'See app/pipeline_engine.py\'s SLA_DEFAULTS and _simulated_minutes() in the Explain the Code tab.',
    },
    kb_section: 'models',
  },
]
