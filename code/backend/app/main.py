"""Drift-Aware Continuous Training Platform backend — FastAPI app entrypoint.

Reference implementation for the paper "A Production-Grade Closed-Loop MLOps
Architecture for Drift-Aware Continuous Training and Deployment Using
Airflow, MLflow, PyTorch, and Kubernetes" (Section 7.3 / Data Availability).
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import alerts, audit, data, drift, electricity, health, joint, pipeline, registry, training
from .seed import bootstrap

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("dact.main")

app = FastAPI(
    title="Drift-Aware Continuous Training Platform API",
    description=(
        "Reference implementation of the paper's closed-loop MLOps architecture: PSI/KS drift "
        "monitoring, a 16-stage Airflow-orchestrated retraining DAG, real PyTorch training, MLflow "
        "experiment tracking + Model Registry, a multi-dimensional quality gate (champion/challenger "
        "evaluation), canary deployment, automatic rollback, SLA monitoring, and a full governance "
        "audit trail — backed by PostgreSQL."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    logger.info("Bootstrapping Drift-Aware Continuous Training Platform: seeding model + running seed pipeline scenarios…")
    bootstrap()
    logger.info("Bootstrap complete — API ready")


app.include_router(health.router)
app.include_router(data.router)
app.include_router(drift.router)
app.include_router(joint.router)
app.include_router(electricity.router)
app.include_router(training.router)
app.include_router(registry.router)
app.include_router(pipeline.router)
app.include_router(alerts.router)
app.include_router(audit.router)

API_CATALOG = {
    "service": "Drift-Aware Continuous Training Platform API",
    "version": "1.0.0",
    "description": "Every endpoint below is documented automatically via FastAPI's OpenAPI schema.",
    "swagger_url": "/docs",
    "redoc_url": "/redoc",
    "openapi_url": "/openapi.json",
    "groups": [
        {"tag": "Health", "description": "Liveness/readiness probes.", "endpoints": [
            {"method": "GET", "path": "/health", "description": "Liveness probe"},
            {"method": "GET", "path": "/ready", "description": "Readiness — DB + fleet seeding status"},
        ]},
        {"tag": "Ingested Data", "description": "Browse every raw/derived table — the actual ingested training data.", "endpoints": [
            {"method": "GET", "path": "/data/summary", "description": "Ingestion counts across every table"},
            {"method": "GET", "path": "/data/datasets", "description": "Browse seeded dataset versions"},
            {"method": "GET", "path": "/data/records", "description": "Browse ingested raw synthetic customer records"},
            {"method": "GET", "path": "/data/data-quality-checks", "description": "Browse data-quality gate results"},
            {"method": "GET", "path": "/data/audit-log", "description": "Governance / audit trail"},
            {"method": "GET", "path": "/data/seed-scenarios", "description": "List the seedable data scenarios"},
        ]},
        {"tag": "Drift Monitoring", "description": "PSI/KS drift detection (paper Section 8).", "endpoints": [
            {"method": "GET", "path": "/api/v1/models/{model}/drift", "description": "Current drift status: reference vs. latest dataset"},
            {"method": "GET", "path": "/api/v1/models/{model}/drift/history", "description": "PSI trend across every ingested dataset version"},
            {"method": "GET", "path": "/api/v1/models/{model}/joint-cell", "description": "Section 8.4 joint cell (DriftLevel x EvaluationLevel); does not train"},
            {"method": "POST", "path": "/api/v1/models/{model}/joint-retrain", "description": "Train only if SIGNIFICANT and EvaluationLevel is not GOOD"},
            {"method": "GET", "path": "/api/v1/electricity/joint-cell", "description": "Electricity Section 8.4 joint cell (fold 0-4); does not train a candidate"},
            {"method": "POST", "path": "/api/v1/electricity/joint-retrain", "description": "Train an Electricity candidate only if SIGNIFICANT and EvaluationLevel is not GOOD"},
        ]},
        {"tag": "Training", "description": "Trigger and inspect the closed-loop retraining pipeline.", "endpoints": [
            {"method": "POST", "path": "/api/v1/models/{model}/training", "description": "Trigger a full 16-stage retraining run"},
            {"method": "GET", "path": "/api/v1/models/{model}/training/{run_id}", "description": "Training run status + every stage"},
            {"method": "GET", "path": "/api/v1/models/{model}/training/history", "description": "Training run history"},
            {"method": "GET", "path": "/api/v1/models/{model}/evaluation/{run_id}", "description": "Evaluation gate result"},
            {"method": "POST", "path": "/api/v1/models/{model}/rollback", "description": "Roll back to the previous production version"},
        ]},
        {"tag": "Models & Registry", "description": "Champion/challenger + version lineage.", "endpoints": [
            {"method": "GET", "path": "/api/v1/models", "description": "List every model + its current champion"},
            {"method": "GET", "path": "/api/v1/models/{model}/versions", "description": "All versions for a model"},
            {"method": "GET", "path": "/api/v1/models/{model}/deployment", "description": "Deployment/canary + rollback timeline"},
        ]},
        {"tag": "Pipeline Runs", "description": "Cross-model DAG run visibility + SLA dashboard.", "endpoints": [
            {"method": "GET", "path": "/pipeline/runs", "description": "List pipeline runs across every model"},
            {"method": "GET", "path": "/pipeline/runs/{run_id}", "description": "Pipeline run detail — every one of the 16 DAG stages"},
            {"method": "GET", "path": "/pipeline/sla", "description": "SLA thresholds + violations across every run"},
        ]},
        {"tag": "Alerts", "description": "Slack/PagerDuty-style notifications.", "endpoints": [
            {"method": "GET", "path": "/alerts", "description": "List alerts"},
            {"method": "POST", "path": "/alerts/{alert_id}/resolve", "description": "Resolve an alert"},
        ]},
        {"tag": "Governance & Audit", "description": "Every promote/reject/rollback/block decision, who/what/when/why.", "endpoints": [
            {"method": "GET", "path": "/audit", "description": "List audit log entries"},
        ]},
    ],
}


@app.get("/docs-catalog", tags=["Meta"], summary="Machine-readable API reference (powers the UI's API Reference tab)")
def docs_catalog():
    return API_CATALOG
