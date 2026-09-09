"""Retraining orchestration DAG (req.md Sec. 9-10, 46 "Airflow Reliability").

The full 16-stage DAG (check_trigger -> ... -> publish_metrics) runs
synchronously inside ONE backend call (`POST /api/v1/models/{model}/training`)
and is individually tracked stage-by-stage as `pipeline_stages` rows, visible
in the UI's "Training Runs" view — this Airflow DAG is the *scheduling and
orchestration* layer (req.md Sec. 9's Apache Airflow box) that decides *when*
and *for which models* that pipeline runs, and inspects the result
afterwards; it does not re-implement the pipeline's own logic.
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

default_args = {
    "owner": "ml-platform",
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
}


def _fetch_models(**_context) -> list[str]:
    resp = requests.get(f"{BACKEND_URL}/api/v1/models", timeout=15)
    resp.raise_for_status()
    names = [row["name"] for row in resp.json()]
    logger.info("Found %d models registered for continuous training: %s", len(names), names)
    return names


def _trigger_scheduled_training(**context) -> list[dict]:
    """req.md Sec. 7.3 Schedule Trigger — dag_run.conf can override {"scenario": ...}
    for manual "Trigger DAG w/ config" runs from the Airflow UI; defaults to healthy."""
    names = context["ti"].xcom_pull(task_ids="fetch_models") or []
    scenario = (context["dag_run"].conf or {}).get("scenario", "healthy") if context.get("dag_run") else "healthy"
    results = []
    for name in names:
        resp = requests.post(
            f"{BACKEND_URL}/api/v1/models/{name}/training",
            json={"trigger_type": "schedule", "scenario": scenario,
                  "trigger_detail": "Weekly scheduled retraining (Airflow DAG, cron 0 2 * * 0)"},
            timeout=120,
        )
        resp.raise_for_status()
        payload = resp.json()
        logger.info("Training run for %s -> status=%s outcome=%s", name, payload["status"], payload.get("outcome"))
        results.append({"model": name, "run_id": payload["id"], "status": payload["status"], "outcome": payload.get("outcome")})
    return results


def _alert_if_required(**context) -> None:
    results = context["ti"].xcom_pull(task_ids="trigger_scheduled_training") or []
    problems = [r for r in results if r["status"] in ("BLOCKED", "FAILED", "REJECTED")]
    if problems:
        logger.warning("ALERT: %d/%d scheduled training runs did NOT reach production: %s",
                        len(problems), len(results), problems)
    else:
        logger.info("All %d scheduled training runs promoted successfully", len(results))


with DAG(
    dag_id="retraining_dag",
    description="req.md Sec. 7-10 — scheduled/manual retraining trigger for every registered model",
    default_args=default_args,
    schedule="0 2 * * 0",  # weekly, matches req.md Sec. 44's example cron
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["continuous-training", "mlflow"],
) as dag:

    fetch_models = PythonOperator(
        task_id="fetch_models",
        python_callable=_fetch_models,
    )

    trigger_scheduled_training = PythonOperator(
        task_id="trigger_scheduled_training",
        python_callable=_trigger_scheduled_training,
    )

    alert_if_required = PythonOperator(
        task_id="alert_if_required",
        python_callable=_alert_if_required,
    )

    fetch_models >> trigger_scheduled_training >> alert_if_required
