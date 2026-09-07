# Synthetic customer-churn datasets (check-in copy)

These files are the **versioned, inspectable** copy of the synthetic telecom-churn
data used by the reference implementation (manuscript Section 7.1).

- No personal data. Every `customer_id` is generated.
- Regenerated with `python scripts/export_dat.py` (requires `numpy` and the
  backend package path). The deploy script also regenerates them.
- Seeds and row counts are recorded in `manifest.json`.

| File | Scenario |
| --- | --- |
| `healthy.csv` | Stable / no injected drift |
| `feature_drift.csv` | Satisfaction and usage shifted |
| `volume_anomaly.csv` | ~12% of expected volume |
| `label_imbalance.csv` | ~2% churn (accuracy-paradox case) |
| `regression.csv` | Heavy label noise |
| `churn_all_scenarios.csv` | Concatenation of the five files |
| `schema.json` | Column dictionary |
| `manifest.json` | Seeds, row counts, churn rates |

The live platform still *generates* batches at pipeline-run time (seeded from
the run id). These CSVs are the frozen, reviewable corpus for the paper and
for git.
