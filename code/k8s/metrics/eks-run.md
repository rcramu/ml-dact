# Local EKS (kind) run snapshot

- Captured: `2026-09-07T17:20:50Z`
- API: `http://127.0.0.1:8166`
- Model: `churn-predictor`
- Runtime: `kind-local-eks`

## Readiness

```json
{
  "database": true,
  "models_seeded": 1,
  "versions_seeded": 5,
  "pipeline_runs_seeded": 6,
  "ready": true
}
```

## Data summary

```json
{
  "models_count": 1,
  "dataset_versions_count": 6,
  "raw_records_count": 7680,
  "model_versions_count": 5,
  "pipeline_runs_count": 6,
  "evaluation_results_count": 5,
  "deployment_events_count": 16,
  "rollback_events_count": 1,
  "alerts_count": 16,
  "audit_logs_count": 7
}
```

## Models

```json
[
  {
    "id": "61cd9c72-c786-4232-b6c2-3409dae4a89a",
    "name": "churn-predictor",
    "description": "Predicts customer churn risk from the synthetic churn dataset described in the paper's Section 7.1; the flagship model exercising the closed-loop drift-aware continuous training architecture (Section 5).",
    "owner_team": "retention-ml",
    "task_type": "classification",
    "created_at": "2026-09-07T17:16:37.675204",
    "champion": {
      "id": "c9440a2e-6cd1-447c-94ee-f511c7c2972d",
      "model_id": "61cd9c72-c786-4232-b6c2-3409dae4a89a",
      "run_id": "083a5b68-7709-4f83-8409-3f270c482dc9",
      "dataset_version_id": "e068385a-da8b-4f1d-8fa8-c8dae21d20ba",
      "version": 1,
      "stage": "production",
      "framework": "PyTorch",
      "architecture": "Feed-forward MLP (8-16-8-1)",
      "hyperparams": {
        "epochs": 120,
        "lr": 0.01
      },
      "mlflow_run_id": "62558bac362941588e2e5151d0e5244e",
      "registry_version": 1,
      "git_commit": "78645b",
      "train_f1": 0.9269195189639223,
      "val_f1": 0.808695652173913,
      "test_f1": 0.7829787234042553,
      "accuracy": 0.7733333333333333,
      "precision": 0.7244094488188977,
      "recall": 0.8518518518518519,
      "roc_auc": 0.8581038303260526,
      "pr_auc": 0.8648828703703861,
      "is_champion": true,
      "promoted_at": "2026-09-07T17:17:49.268955",
      "created_at": "2026-09-07T17:17:06.277884"
    },
    "version_count": 5,
    "run_count": 6
  }
]
```

## Versions (5 rows)

| Version | Stage | Champion | F1 | Precision | Recall | ROC-AUC |
| --- | --- | --- | --- | --- | --- | --- |
| 5 | rejected | False | 0.7632850241545893 | 0.7452830188679245 | 0.7821782178217822 | 0.8630629191951453 |
| 4 | rejected | False | 0.7164179104477612 | 0.5853658536585366 | 0.9230769230769231 | 0.7797202797202797 |
| 3 | rejected | False | 0.0 | 0.0 | 0.0 | 0.6921921921921921 |
| 2 | rolled_back | False | 0.9484029484029484 | 0.919047619047619 | 0.9796954314720813 | 0.9214104423495287 |
| 1 | production | True | 0.7829787234042553 | 0.7244094488188977 | 0.8518518518518519 | 0.8581038303260526 |

## Training runs (6)

| ID | Trigger | Status | Outcome | Scenario |
| --- | --- | --- | --- | --- |
| `f2738c59` | manual | REJECTED | MODEL_NOT_PROMOTED | Re-run after rollback with a corrected dataset |
| `557897c0` | performance | REJECTED | MODEL_NOT_PROMOTED | Production F1 dipped below 0.85 - investigating with a larger labeled sample |
| `55d0d049` | schedule | REJECTED | MODEL_NOT_PROMOTED | Weekly scheduled retraining (cron 0 2 * * 0) |
| `40e14a63` | drift | SUCCESS | PROMOTED | Feature drift detected by the Drift Monitoring tab: PSI=0.81 on customer_satisfaction/usage_score - Experiment 2/3: drift then automated retraining |
| `7413fc79` | data_availability | BLOCKED | DATA_VOLUME_ALERT | 1,000,000 new labeled records available (simulated volume anomaly) |
| `083a5b68` | schedule | SUCCESS | PROMOTED | Weekly scheduled retraining (cron 0 2 * * 0) - Experiment 1: baseline |

## SLA

```json
{
  "stage_thresholds": {
    "check_trigger": 1.0,
    "check_volume_anomaly": 5.0,
    "compare_champion": 5.0,
    "deploy_production": 15.0,
    "deploy_stage": 15.0,
    "evaluate_model": 20.0,
    "evaluation_gate": 2.0,
    "feature_engineering": 30.0,
    "log_mlflow": 5.0,
    "post_deployment_test": 10.0,
    "prepare_dataset": 10.0,
    "production_gate": 2.0,
    "publish_metrics": 5.0,
    "register_model": 5.0,
    "train_model": 120.0,
    "validate_dataset": 10.0
  },
  "violations": [
    {
      "id": "ee04bde9-4239-476e-be1b-ac535e2ccef7",
      "run_id": "557897c0-97a8-4f88-8723-6ce0fcfce530",
      "stage_name": "train_model",
      "actual_minutes": 141.6,
      "max_minutes": 120.0,
      "created_at": "2026-09-07T17:17:48.853528"
    }
  ],
  "compliance_pct": 83.3,
  "total_runs": 6,
  "runs_with_violation": 1
}
```

## Drift (current)

```json
{
  "reference_dataset_version_id": "e068385a-da8b-4f1d-8fa8-c8dae21d20ba",
  "production_dataset_version_id": "4c6b23fa-d131-4f37-884c-f778006e9a42",
  "psi_overall": 0.011,
  "drift_level": "NORMAL",
  "thresholds": {
    "warning": 0.1,
    "critical": 0.25
  },
  "features": [
    {
      "feature": "age",
      "psi": 0.0233,
      "ks_statistic": 0.05,
      "ks_p_value": 0.047,
      "reference_mean": 47.1687,
      "production_mean": 45.706,
      "drift_level": "NORMAL"
    },
    {
      "feature": "tenure_days",
      "psi": 0.0224,
      "ks_statistic": 0.04,
      "ks_p_value": 0.1813,
      "reference_mean": 393.302,
      "production_mean": 386.874,
      "drift_level": "NORMAL"
    },
    {
      "feature": "monthly_charges",
      "psi": 0.0162,
      "ks_statistic": 0.0407,
      "ks_p_value": 0.1673,
      "reference_mean": 83.7725,
      "production_mean": 85.9918,
      "drift_level": "NORMAL"
    },
    {
      "feature": "support_tickets",
      "psi": 0.0059,
      "ks_statistic": 0.0287,
      "ks_p_value": 0.5688,
      "reference_mean": 1.5067,
      "production_mean": 1.4693,
      "drift_level": "NORMAL"
    },
    {
      "feature": "usage_score",
      "psi": 0.0111,
      "ks_statistic": 0.026,
      "ks_p_value": 0.6913,
      "reference_mean": 0.5512,
      "production_mean": 0.5438,
      "drift_level": "NORMAL"
    },
    {
      "feature": "service_count",
      "psi": 0.0036,
      "ks_statistic": 0.0133,
      "ks_p_value": 0.9993,
      "reference_mean": 1.978,
      "production_mean": 1.972,
      "drift_level": "NORMAL"
    },
    {
      "feature": "customer_satisfaction",
      "psi": 0.0053,
      "ks_statistic": 0.0193,
      "ks_p_value": 0.942,
      "reference_mean": 0.6961,
      "production_mean": 0.6959,
      "drift_level": "NORMAL"
    },
    {
      "feature": "is_month_to_month",
      "psi": 0.0,
      "ks_statistic": 0.0193,
      "ks_p_value": 0.942,
      "reference_mean": 0.398,
      "production_mean": 0.4173,
      "drift_level": "NORMAL"
    }
  ]
}
```

