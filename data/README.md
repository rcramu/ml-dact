# Reviewable data (repo root)

Copies of the paper corpus and kind-run snapshots, collected here so reviewers
do not have to walk the implementation tree. The same files remain under
`code/data/` and `code/k8s/metrics/`.

## Corpus (from `code/data/`)

No personal data. Every `customer_id` is generated. Live pipeline runs still
synthesize a batch at trigger time.

| File | What it is |
| --- | --- |
| `healthy.csv` | Stable / no injected drift |
| `feature_drift.csv` | Satisfaction and usage shifted |
| `volume_anomaly.csv` | ~12% of expected volume |
| `label_imbalance.csv` | ~2% churn (accuracy-paradox case) |
| `regression.csv` | Heavy label noise |
| `churn_all_scenarios.csv` | Concatenation of the five files |
| `schema.json` | Column dictionary |
| `manifest.json` | Seeds, row counts, churn rates |
| `ibm-telco-churn.csv` | Public IBM Telco sample (exploratory Tables 13, 15, 20) |
| `electricity.csv` | Public Electricity / Elec2 sample (exploratory Tables 17, 19) |

## Kind-run snapshots (from `code/k8s/metrics/`)

| File | Table / use |
| --- | --- |
| `eks-run.json`, `eks-run.md` | First confirmatory seed |
| `replicates.json` | Table 6 |
| `order-sensitivity.json` | Table 7 |
| `h1-per-feature.json` | Table 8 |
| `threshold-sweep.json` | Table 9 |
| `live-ablation.json` | Table 10 |
| `section-84.json` | Table 11 |
| `second-family.json` | Table 12 |
| `telco-transfer.json` | Table 13 |
| `order-factorial.json` | Table 14 |
| `telco-calibrated.json` | Table 15 |
| `order-replicates.json` | Table 16 |
| `electricity-natural.json` | Table 17 |
| `live-joint-airflow.json` | Table 18 |
| `electricity-live-airflow.json` | Table 19 |
| `telco-fulltable.json` | Table 20 |
