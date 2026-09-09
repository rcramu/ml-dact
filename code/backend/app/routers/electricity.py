"""Live Section 8.4 joint cell for Electricity (Elec2).

Exploratory only. Model name is fixed to electricity-joint. Folds are 0..4.
GET scores the cell and does not train a candidate. POST trains only on fire.
Never touches confirmatory registry names.
"""
from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models as m
from .. import pipeline_engine as pe
from .. import schemas
from .. import serializers as ser
from ..database import get_db
from ..ml import electricity as elec

router = APIRouter(prefix="/api/v1/electricity", tags=["Electricity Joint Cell"])

PUBLIC_RESPONSE_KEYS = (
    "model", "fold", "n_ref", "n_prod", "ref_date_min", "ref_date_max",
    "prod_date_min", "prod_date_max", "psi_mean", "psi_per_feature",
    "drift_level", "champion_f1_ref", "champion_precision_ref", "champion_recall_ref",
    "champion_first_version", "champion_first_reasons", "champion_f1_prod",
    "champion_precision_prod", "champion_recall_prod", "evaluation_level",
    "matrix_cell", "joint_retrain", "predicate", "candidate_trained",
    "candidate_f1_prod", "candidate_precision_prod", "candidate_recall_prod",
    "delta_f1_on_prod", "gate", "regression_pct", "gate_reasons",
)


def _public(rec: dict) -> dict:
    return {k: rec.get(k) for k in PUBLIC_RESPONSE_KEYS}


def _require_fold(fold: int) -> int:
    if fold not in range(elec.N_FOLDS):
        raise HTTPException(400, "fold must be 0, 1, 2, 3, or 4")
    return fold


def _get_or_create_model(db: Session) -> m.TrainedModel:
    model = db.query(m.TrainedModel).filter_by(name=elec.MODEL_NAME).one_or_none()
    if model is None:
        model = m.TrainedModel(
            name=elec.MODEL_NAME,
            task_type="classification",
            owner_team="energy-ml",
            description="Exploratory Electricity (Elec2) live Airflow joint-cell model. Not confirmatory.",
        )
        db.add(model)
        db.flush()
    return model


def _score(fold: int) -> dict:
    try:
        return elec.score_fold(fold, train_candidate=False)
    except FileNotFoundError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/joint-cell", summary="Score Electricity Section 8.4 joint cell; does not train a candidate")
def get_joint_cell(fold: int = Query(..., ge=0, le=4)):
    _require_fold(fold)
    return _public(_score(fold))


@router.post("/joint-retrain", summary="Train an Electricity candidate only if the joint cell fires")
def post_joint_retrain(body: schemas.ElectricityJointRetrainRequest, db: Session = Depends(get_db)):
    fold = _require_fold(body.fold)
    pe.ensure_sla_config(db)
    model = _get_or_create_model(db)
    decision = _score(fold)
    if not decision["joint_retrain"]:
        pe._audit(
            db,
            action="joint_hold",
            resource_type="model",
            resource_id=model.id,
            detail=(
                f"{elec.MODEL_NAME} fold={fold}: hold "
                f"{decision['drift_level']} x {decision['evaluation_level']} "
                f"({decision['matrix_cell']})"
            ),
        )
        db.commit()
        return {"decision": _public(decision), "trained": False, "run": None}

    trained = elec.score_fold(fold, train_candidate=True)
    run = pe._new_run(
        db,
        model,
        "joint",
        (body.trigger_detail or f"Airflow electricity_joint_dag fold={fold}")[:200],
    )
    pe._alert(
        db,
        run_id=run.id,
        model_version_id=None,
        category="training_started",
        severity="INFO",
        channel="slack",
        message=f"{elec.MODEL_NAME} fold={fold}: joint cell FIRE {trained['drift_level']} x {trained['evaluation_level']}",
    )

    s = pe._start(db, run, "check_trigger")
    pe._finish(db, run, s, "SUCCESS", {"fold": fold, "trigger_type": "joint", "corpus": "electricity"})

    s = pe._start(db, run, "validate_dataset")
    pe._finish(db, run, s, "SUCCESS", {"n_ref": trained["n_ref"], "n_prod": trained["n_prod"], "source": "frozen csv"})

    for name in ("check_volume_anomaly", "prepare_dataset", "feature_engineering"):
        s = pe._start(db, run, name)
        pe._finish(db, run, s, "SUCCESS", {"note": "Electricity chronological block; no volume gate"})

    s = pe._start(db, run, "train_model")
    pe._finish(
        db, run, s, "SUCCESS",
        {"framework": "sklearn HistGradientBoostingClassifier", "candidate_f1": trained["candidate_f1_prod"]},
    )

    s = pe._start(db, run, "log_mlflow")
    pe._finish(db, run, s, "SUCCESS", {"skipped": "electricity exploratory; no MLflow artifact"})

    s = pe._start(db, run, "evaluate_model")
    pe._finish(
        db, run, s, "SUCCESS",
        {
            "champion_f1_prod": trained["champion_f1_prod"],
            "candidate_f1_prod": trained["candidate_f1_prod"],
        },
    )

    s = pe._start(db, run, "compare_champion")
    pe._finish(
        db, run, s, "SUCCESS",
        {"champion_f1_ref": trained["champion_f1_ref"], "note": "gate uses ref-block champion metrics"},
    )

    gate_ok = trained["gate"] == "PROMOTED"
    s = pe._start(db, run, "evaluation_gate")
    pe._finish(
        db, run, s, "SUCCESS" if gate_ok else "FAILED",
        {"gate_result": "PASS" if gate_ok else "FAIL", "reasons": trained["gate_reasons"]},
    )

    version_number = pe._next_version_number(db, model.id)
    candidate = m.ModelVersion(
        model_id=model.id,
        run_id=run.id,
        version=version_number,
        stage="candidate",
        framework="sklearn",
        architecture="HistGradientBoostingClassifier (Elec2)",
        hyperparams_json=json.dumps({"max_depth": 6, "learning_rate": 0.10, "max_iter": 120, "fold": fold}),
        test_f1=trained["candidate_f1_prod"] or 0.0,
        precision=trained["candidate_precision_prod"] or 0.0,
        recall=trained["candidate_recall_prod"] or 0.0,
    )
    db.add(candidate)
    db.flush()
    run.candidate_version_id = candidate.id
    db.add(m.EvaluationResult(
        run_id=run.id,
        candidate_version_id=candidate.id,
        candidate_metrics_json=json.dumps(trained.get("candidate_metrics") or {}),
        champion_metrics_json=json.dumps(trained.get("champion_metrics") or {}),
        regression_pct=trained["regression_pct"],
        gate_result="PASS" if gate_ok else "FAIL",
        reasons=trained["gate_reasons"] or "",
    ))
    db.flush()

    if not gate_ok:
        candidate.stage = "rejected"
        run.status = "REJECTED"
        run.outcome = "MODEL_NOT_PROMOTED"
        run.completed_at = datetime.utcnow()
        pe._skip_remaining(db, run, s.stage_order + 1)
        pe._audit(
            db,
            action="reject",
            resource_type="model_version",
            resource_id=candidate.id,
            detail=f"Electricity fold={fold} gate FAILED: {trained['gate_reasons']}",
        )
        db.commit()
        return {"decision": _public(trained), "trained": True, "run": ser.pipeline_run_dict(run, include_stages=True)}

    for name in ("register_model", "deploy_stage", "post_deployment_test", "production_gate"):
        s = pe._start(db, run, name)
        pe._finish(db, run, s, "SUCCESS", {"note": "electricity exploratory; canary fractions simulated"})
    s = pe._start(db, run, "deploy_production")
    pe._deploy_and_promote(db, run, candidate, model)
    pe._finish(db, run, s, "SUCCESS", {"fold": fold})
    s = pe._start(db, run, "publish_metrics")
    run.status = "SUCCESS"
    run.outcome = "PROMOTED"
    run.completed_at = datetime.utcnow()
    pe._finish(db, run, s, "SUCCESS", {"promoted_version": candidate.version})
    db.commit()
    return {"decision": _public(trained), "trained": True, "run": ser.pipeline_run_dict(run, include_stages=True)}
