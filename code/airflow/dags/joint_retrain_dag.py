"""Section 8.4 joint-cell trigger (exploratory models only).

Scores GET /joint-cell and POSTs /joint-retrain only for model names that
start with churn-predictor-joint. Never touches confirmatory registry names.
dag_run.conf: {"model": "...", "scenario": "...", "seed": 9801}
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta

import requests
from airflow import DAG
from airflow.operators.python import PythonOperator

logger = logging.getLogger(__name__)

BACKEND_URL = os.environ.get("BACKEND_URL", "http://backend:8000")
JOINT_PREFIX = "churn-predictor-joint"
ALLOWED_SCENARIOS = {
    "healthy",
    "volume_anomaly",
    "feature_drift",
    "label_imbalance",
    "regression",
}

default_args = {
    "owner": "ml-platform",
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}


def _conf(context) -> dict:
    return (context.get("dag_run").conf or {}) if context.get("dag_run") else {}


def _decide_and_maybe_train(**context) -> dict:
    conf = _conf(context)
    model = str(conf.get("model") or "")
    scenario = str(conf.get("scenario") or "feature_drift")
    seed = int(conf.get("seed") or 42)
    if not model.startswith(JOINT_PREFIX):
        raise ValueError(f"refusing model {model!r}: joint DAG only accepts {JOINT_PREFIX}*")
    if scenario not in ALLOWED_SCENARIOS:
        raise ValueError(f"scenario must be one of {sorted(ALLOWED_SCENARIOS)}")
    resp = requests.post(
        f"{BACKEND_URL}/api/v1/models/{model}/joint-retrain",
        json={
            "scenario": scenario,
            "seed": seed,
            "trigger_detail": f"Airflow joint_retrain_dag {scenario} seed={seed}",
        },
        timeout=300,
    )
    resp.raise_for_status()
    payload = resp.json()
    decision = payload.get("decision") or {}
    logger.info(
        "%s %s PSI=%s %s x %s fire=%s trained=%s",
        model, scenario, decision.get("psi_mean"), decision.get("drift_level"),
        decision.get("evaluation_level"), decision.get("joint_retrain"), payload.get("trained"),
    )
    return payload


with DAG(
    dag_id="joint_retrain_dag",
    description="Section 8.4: retrain only if SIGNIFICANT and EvaluationLevel is not GOOD",
    default_args=default_args,
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["joint-cell", "section-84"],
) as dag:

    decide_and_maybe_train = PythonOperator(
        task_id="decide_and_maybe_train",
        python_callable=_decide_and_maybe_train,
    )
