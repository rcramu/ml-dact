"""MLflow tracking + Model Registry helpers (req.md Sec. 17-19, 39-40, 43-44)."""
import logging

import mlflow
from mlflow.tracking import MlflowClient

from ..config import settings

logger = logging.getLogger("continuoustraining.mlflow")

_configured = False


def _ensure_configured():
    global _configured
    if _configured:
        return
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment(settings.mlflow_experiment)
    _configured = True


def log_training_run(run_name: str, params: dict, metrics: dict, tags: dict | None = None) -> str:
    """req.md Sec. 17 — every training execution creates its own MLflow run."""
    try:
        _ensure_configured()
        with mlflow.start_run(run_name=run_name) as run:
            mlflow.log_params(params)
            mlflow.log_metrics(metrics)
            if tags:
                mlflow.set_tags(tags)
            return run.info.run_id
    except Exception:  # pragma: no cover - MLflow must never break the pipeline
        logger.warning("MLflow logging failed for run %s", run_name, exc_info=True)
        return ""


def register_run_as_model_version(run_id: str, register_as: str) -> int | None:
    """req.md Sec. 18 "register_model" DAG stage — only called AFTER the evaluation gate passes."""
    if not run_id:
        return None
    try:
        _ensure_configured()
        client = MlflowClient()
        try:
            client.create_registered_model(register_as)
        except Exception:
            pass  # already exists
        mv = client.create_model_version(name=register_as, source=f"runs:/{run_id}/model", run_id=run_id)
        return int(mv.version)
    except Exception:
        logger.warning("MLflow registration failed for run %s -> %s", run_id, register_as, exc_info=True)
        return None


def transition_stage(register_as: str, version: int, stage: str) -> None:
    """req.md Sec. 18 — move a registered model version between Staging/Production/Archived."""
    try:
        _ensure_configured()
        MlflowClient().transition_model_version_stage(name=register_as, version=str(version), stage=stage)
    except Exception:
        logger.warning("MLflow stage transition failed for %s v%s -> %s", register_as, version, stage, exc_info=True)


def lineage_url(run_id: str) -> str:
    if not run_id:
        return ""
    return f"{settings.mlflow_tracking_uri}/#/experiments/0/runs/{run_id}"
