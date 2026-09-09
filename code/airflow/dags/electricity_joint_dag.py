"""Electricity Section 8.4 joint-cell trigger (exploratory only).

POSTs /api/v1/electricity/joint-retrain for fold 0..4. Does not accept a
model name. Never touches confirmatory registry names.
dag_run.conf: {"fold": 0}
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
ALLOWED_FOLDS = {0, 1, 2, 3, 4}

default_args = {
    "owner": "ml-platform",
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}


def _conf(context) -> dict:
    return (context.get("dag_run").conf or {}) if context.get("dag_run") else {}


def _decide_and_maybe_train(**context) -> dict:
    conf = _conf(context)
    try:
        fold = int(conf.get("fold"))
    except (TypeError, ValueError) as exc:
        raise ValueError("fold must be an integer 0..4") from exc
    if fold not in ALLOWED_FOLDS:
        raise ValueError(f"refusing fold {fold!r}: electricity DAG only accepts 0..4")
    resp = requests.post(
        f"{BACKEND_URL}/api/v1/electricity/joint-retrain",
        json={
            "fold": fold,
            "trigger_detail": f"Airflow electricity_joint_dag fold={fold}",
        },
        timeout=300,
    )
    resp.raise_for_status()
    payload = resp.json()
    decision = payload.get("decision") or {}
    logger.info(
        "electricity-joint fold=%s PSI=%s %s x %s fire=%s trained=%s",
        fold, decision.get("psi_mean"), decision.get("drift_level"),
        decision.get("evaluation_level"), decision.get("joint_retrain"), payload.get("trained"),
    )
    return payload


with DAG(
    dag_id="electricity_joint_dag",
    description="Electricity Section 8.4: retrain only if SIGNIFICANT and EvaluationLevel is not GOOD",
    default_args=default_args,
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["joint-cell", "section-84", "electricity"],
) as dag:

    decide_and_maybe_train = PythonOperator(
        task_id="decide_and_maybe_train",
        python_callable=_decide_and_maybe_train,
    )
