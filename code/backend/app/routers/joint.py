"""Section 8.4 joint cell on the live API.

Retrain = (DriftLevel == SIGNIFICANT) and (EvaluationLevel != GOOD).
EvaluationLevel is GOOD iff the current champion's F1 on a newly generated
scenario test split is >= minimum_f1. This endpoint does not train a
candidate. POST /joint-retrain trains only when the cell fires.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

import numpy as np

from .. import data_generator as gen
from .. import models as m
from .. import pipeline_engine as pe
from .. import schemas
from ..config import settings
from ..database import get_db
from ..ml import champion_store
from ..ml.drift import drift_level, psi_numeric
from ..ml.evaluation_metrics import classification_metrics
from ..ml.pytorch_trainer import predict
from .drift import _get_model

router = APIRouter(prefix="/api/v1/models", tags=["Joint Cell"])

ALLOWED_SCENARIOS = {
    "healthy",
    "volume_anomaly",
    "feature_drift",
    "label_imbalance",
    "regression",
}
F1_GOOD = settings.minimum_f1


def _cell(drift: str, ev: str) -> str:
    table = {
        ("NORMAL", "GOOD"): "Continue",
        ("NORMAL", "BAD"): "Investigate model",
        ("NORMAL", "UNKNOWN"): "Continue monitoring",
        ("WARNING", "GOOD"): "Continue",
        ("WARNING", "BAD"): "Investigate model",
        ("WARNING", "UNKNOWN"): "Continue monitoring",
        ("SIGNIFICANT", "GOOD"): "Investigate",
        ("SIGNIFICANT", "BAD"): "Retrain / review",
        ("SIGNIFICANT", "UNKNOWN"): "Obtain ground truth",
    }
    return table.get((drift, ev), "unspecified")


def _orm_to_dicts(rows: list[m.RawRecord]) -> list[dict]:
    return [
        {
            "split": r.split,
            "age": r.age,
            "tenure_days": r.tenure_days,
            "monthly_charges": r.monthly_charges,
            "support_tickets": r.support_tickets,
            "usage_score": r.usage_score,
            "service_count": r.service_count,
            "customer_satisfaction": r.customer_satisfaction,
            "is_month_to_month": r.is_month_to_month,
            "label": r.label,
        }
        for r in rows
    ]


def _mean_psi(ref: list[dict], prod: list[dict]) -> float:
    if not ref or not prod:
        return 0.0
    vals = []
    for name in gen.FEATURE_NAMES:
        a = np.array([float(r[name]) if not isinstance(r[name], bool) else float(int(r[name])) for r in ref], dtype=float)
        b = np.array([float(r[name]) if not isinstance(r[name], bool) else float(int(r[name])) for r in prod], dtype=float)
        vals.append(psi_numeric(a, b))
    return float(np.mean(vals)) if vals else 0.0


def _score_joint(db: Session, trained_model: m.TrainedModel, scenario: str, seed: int) -> dict:
    if scenario not in ALLOWED_SCENARIOS:
        raise HTTPException(400, f"scenario must be one of {sorted(ALLOWED_SCENARIOS)}")
    datasets = (
        db.query(m.DatasetVersion).filter_by(model_id=trained_model.id)
        .order_by(m.DatasetVersion.created_at.asc()).all()
    )
    reference = next((d for d in datasets if d.scenario == "healthy"), datasets[0] if datasets else None)
    if reference is None:
        raise HTTPException(404, "no healthy reference dataset; train a champion first")
    ref_rows = _orm_to_dicts(
        db.query(m.RawRecord).filter_by(dataset_version_id=reference.id).all()
    )
    batch = gen.generate_scenario(scenario, seed, settings.expected_volume)
    psi = _mean_psi(ref_rows, batch)
    dlev = drift_level(psi)
    champion = pe._current_champion(db, trained_model.id)
    ev_level = "UNKNOWN"
    champ_f1 = None
    n_test = 0
    if champion is not None:
        loaded = champion_store.load_weights(champion.id)
        if loaded is not None:
            model, threshold = loaded
            x_te, y_te = gen.records_to_arrays(batch, "test")
            n_test = int(len(y_te))
            if n_test >= 5:
                probs = predict(model, x_te)
                preds = (probs >= threshold).astype(int)
                metrics = classification_metrics(probs, preds, y_te)
                champ_f1 = round(metrics["f1"], 4)
                ev_level = "GOOD" if metrics["f1"] >= F1_GOOD else "BAD"
            else:
                ev_level = "UNKNOWN"
        else:
            ev_level = "UNKNOWN"
    fire = dlev == "SIGNIFICANT" and ev_level != "GOOD"
    return {
        "model": trained_model.name,
        "scenario": scenario,
        "seed": seed,
        "psi_mean": round(psi, 4),
        "drift_level": dlev,
        "champion_version": None if champion is None else champion.version,
        "champion_f1_on_batch": champ_f1,
        "n_test": n_test,
        "evaluation_level": ev_level,
        "matrix_cell": _cell(dlev, ev_level),
        "joint_retrain": fire,
        "predicate": "Retrain = (DriftLevel == SIGNIFICANT) and (EvaluationLevel != GOOD)",
    }


@router.get("/{model}/joint-cell", summary="Score Section 8.4 joint cell; does not train")
def get_joint_cell(
    model: str,
    scenario: str = Query(..., description="healthy | volume_anomaly | feature_drift | label_imbalance | regression"),
    seed: int = Query(42, ge=1, le=2_000_000_000),
    db: Session = Depends(get_db),
):
    trained_model = _get_model(db, model)
    return _score_joint(db, trained_model, scenario, seed)


@router.post("/{model}/joint-retrain", summary="Train only if the Section 8.4 joint cell fires")
def post_joint_retrain(model: str, body: schemas.JointRetrainRequest, db: Session = Depends(get_db)):
    trained_model = _get_model(db, model)
    decision = _score_joint(db, trained_model, body.scenario, body.seed)
    if not decision["joint_retrain"]:
        pe._audit(
            db,
            action="joint_hold",
            resource_type="model",
            resource_id=trained_model.id,
            detail=(
                f"{trained_model.name} {body.scenario}: hold "
                f"{decision['drift_level']} x {decision['evaluation_level']} "
                f"({decision['matrix_cell']})"
            ),
        )
        db.commit()
        return {"decision": decision, "trained": False, "run": None}
    run = pe.run_pipeline(
        db,
        trained_model,
        trigger_type="joint",
        trigger_detail=body.trigger_detail or (
            f"Airflow joint cell FIRE {decision['drift_level']} x {decision['evaluation_level']} "
            f"PSI={decision['psi_mean']}"
        ),
        scenario=body.scenario,
    )
    from .. import serializers as ser
    return {
        "decision": decision,
        "trained": True,
        "run": ser.pipeline_run_dict(run, include_stages=True),
    }
