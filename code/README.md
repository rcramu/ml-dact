# Drift-Aware Continuous Training Platform (reference implementation)

Reference implementation for the paper **"A Closed-Loop MLOps Architecture for Drift-Aware,
Quality-Gated Continuous Training: Design and Observational Case Study"**.

It automates the closed loop **monitor -> detect drift (PSI/KS) -> retrain -> evaluate -> quality-gate
-> deploy -> monitor** for a synthetic customer-churn classifier (Section 7.1 of the paper): a real
16-stage Airflow-orchestrated retraining DAG, real PyTorch training, MLflow experiment tracking +
Model Registry, a multi-dimensional quality gate (Section 9), canary deployment, and automatic
rollback — backed by PostgreSQL.

## Stack

| Layer | Technology |
| --- | --- |
| Database | PostgreSQL 16 (also backs Airflow's own metadata store) |
| Experiment tracking + Model Registry | MLflow (its own container) |
| Model training | PyTorch (feed-forward MLP, trained from scratch every run) |
| Drift detection | PSI / Kolmogorov-Smirnov, implemented from scratch with SciPy/NumPy (paper Section 8) |
| Evaluation metrics | scikit-learn |
| Orchestration (retraining schedule) | Apache Airflow (LocalExecutor) |
| Backend | Python, FastAPI, SQLAlchemy |
| Frontend | React 18 + Vite, served by nginx |
| Container orchestration | Docker Compose **or** local Kubernetes via kind (`k8s/`, EKS-shaped objects) |

## Quick start (Docker Compose)

```bash
cd code
cp .env.example .env
docker compose up --build
```

This starts **six** containers:

| Service | URL | Notes |
| --- | --- | --- |
| Frontend (React console) | http://localhost:3066 | Drift Monitoring, Training Runs, Models & Registry, Deployment & Rollback, Alerts, Ingested Data, Knowledge Base |
| Backend API | http://localhost:8166 | FastAPI |
| Swagger UI | http://localhost:8166/docs | Auto-generated from the API |
| ReDoc | http://localhost:8166/redoc | Alternate API docs view |
| MLflow tracking UI | http://localhost:5026 | Every training run + Model Registry versions |
| Airflow | http://localhost:8766 | admin/admin — `retraining_dag` |
| PostgreSQL | localhost:5476 | db `dact_training`, user `dact_user` (Airflow uses a second `airflow` db on the same instance) |

On first boot the backend automatically:

1. Creates the database schema.
2. Seeds one flagship model, `churn-predictor`, against the synthetic churn dataset of Section 7.1.
3. Runs it through **5 training scenarios**, matching the paper's experimental narrative (Sections 7.2, 11-13):
   - `healthy` (schedule trigger, Experiment 1 — baseline) -> promoted, becomes the first champion (v1)
   - `volume_anomaly` (data-availability trigger) -> **BLOCKED** before training even starts (`DATA_VOLUME_ALERT`)
   - `feature_drift` (drift trigger, PSI-triggered — Experiments 2/3) -> promoted, becomes the new champion (v2)
   - `label_imbalance` (schedule trigger) -> trained, but **rejected** by the quality gate (`DATA_QUALITY_WARNING` + low recall)
   - `regression` (performance trigger) -> trained, but **rejected** by the quality gate (regression exceeds budget)
4. Simulates a production regression on the v2 champion and calls the same `rollback()` used by the
   UI's manual rollback button — v1 is restored to production.
5. Runs one more healthy training run so the model ends in a clean, promoted state.

No manual seeding or training step is required — just `docker compose up --build`.

The Airflow DAG (`retraining_dag`) is created **paused** — open http://localhost:8766, unpause it,
and trigger a run (or wait for its weekly `0 2 * * 0` schedule) to see it call the same
`POST /api/v1/models/{model}/training` endpoint the UI's "Trigger training" button uses.

Checked-in synthetic datasets (no personal data) live in [`dat/`](dat/). Regenerate with
`python scripts/export_dat.py` (or via `k8s/deploy-local-eks.sh`).

## Local EKS (kind)

To run the same stack on local Kubernetes, collect live metrics, and keep `dat/` in sync:

```bash
./k8s/deploy-local-eks.sh
```

See [`k8s/README.md`](k8s/README.md). Metrics land in `k8s/metrics/eks-run.json`.

Stop everything with:

```bash
docker compose down          # keep all volumes
docker compose down -v       # also delete all volumes (fresh reseed on next `up`)
```

## API

Every endpoint is documented automatically via FastAPI's OpenAPI schema (Swagger at `/docs`, ReDoc at
`/redoc`) and is also summarized in the UI's **API Reference** tab. Key endpoints:

```
GET  /api/v1/models/{model}/drift              Current drift status: reference vs. latest dataset (Section 8)
GET  /api/v1/models/{model}/drift/history       PSI trend across every ingested dataset version
POST /api/v1/models/{model}/training            Trigger a full 16-stage retraining run
GET  /api/v1/models/{model}/training/{run_id}   Training run status + every stage
GET  /api/v1/models/{model}/training/history    Training run history
GET  /api/v1/models/{model}/evaluation/{run_id} Evaluation gate result (Section 9)
POST /api/v1/models/{model}/rollback            Roll back to the previous production version
GET  /api/v1/models                            List models + current champion
GET  /api/v1/models/{model}/versions            Full version lineage
GET  /api/v1/models/{model}/deployment          Canary/rollback timeline
GET  /pipeline/runs, /pipeline/runs/{run_id}    Cross-model DAG run visibility
GET  /pipeline/sla                             SLA thresholds + violations
GET  /alerts, POST /alerts/{id}/resolve         Slack/PagerDuty-style notifications
GET  /audit                                    Governance / audit trail
GET  /data/summary, /data/datasets, /data/records, ...   Ingested data
```

## Environment variables

Copy `.env.example` to `.env` to override defaults (training epochs, quality-gate thresholds, etc.) —
the stack runs fully offline out of the box with no external services or API keys required.

## Knowledge Base

The UI's **Knowledge Base** section (left sidebar, bottom group) covers: About this Project, an
illustrated Concept Preview (with a flashcard deck), a searchable Term Glossary, Formulas &
Algorithms (PSI, the quality-gate formula, the PyTorch model, SLA math), Architecture, Explain the
Code, Tools & Frameworks, and a "Check My Understanding" self-check quiz (7+ questions per topic).
