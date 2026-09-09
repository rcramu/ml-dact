"""Training/evaluation/rollback API — implements req.md Sec. 43 literally:
POST /api/v1/models/{model}/training, GET .../training/{run_id}, GET .../training/history,
GET .../evaluation/{run_id}, POST .../rollback.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models as m
from .. import pipeline_engine as pe
from .. import schemas
from .. import serializers as ser
from ..database import get_db

router = APIRouter(prefix="/api/v1/models", tags=["Training"])


def _get_model(db: Session, name: str) -> m.TrainedModel:
    model = db.query(m.TrainedModel).filter_by(name=name).one_or_none()
    if model is None:
        raise HTTPException(404, f"model '{name}' not found")
    return model


@router.post("/{model}/training", summary="Trigger a full 16-stage retraining run (req.md Sec. 9-10, 43)")
def trigger_training(model: str, body: schemas.TriggerTrainingRequest, db: Session = Depends(get_db)):
    trained_model = _get_model(db, model)
    run = pe.run_pipeline(
        db, trained_model, trigger_type=body.trigger_type,
        trigger_detail=body.trigger_detail or f"Manual trigger via API ({body.scenario})", scenario=body.scenario,
    )
    return ser.pipeline_run_dict(run, include_stages=True)


@router.get("/{model}/training/history", summary="Training run history for a model (req.md Sec. 43)")
def training_history(model: str, db: Session = Depends(get_db), limit: int = Query(50, le=200)):
    trained_model = _get_model(db, model)
    rows = (
        db.query(m.PipelineRun).filter_by(model_id=trained_model.id)
        .order_by(m.PipelineRun.started_at.desc()).limit(limit).all()
    )
    return [ser.pipeline_run_dict(r) for r in rows]


@router.get("/{model}/training/{run_id}", summary="Training run status + every stage (req.md Sec. 43)")
def training_status(model: str, run_id: str, db: Session = Depends(get_db)):
    trained_model = _get_model(db, model)
    run = db.query(m.PipelineRun).filter_by(id=run_id, model_id=trained_model.id).one_or_none()
    if run is None:
        raise HTTPException(404, "training run not found")
    return ser.pipeline_run_dict(run, include_stages=True)


@router.get("/{model}/evaluation/{run_id}", summary="Evaluation gate result for a training run (req.md Sec. 43)")
def evaluation_detail(model: str, run_id: str, db: Session = Depends(get_db)):
    trained_model = _get_model(db, model)
    run = db.query(m.PipelineRun).filter_by(id=run_id, model_id=trained_model.id).one_or_none()
    if run is None:
        raise HTTPException(404, "training run not found")
    result = db.query(m.EvaluationResult).filter_by(run_id=run.id).one_or_none()
    if result is None:
        raise HTTPException(404, "this run has no evaluation result (it may have been blocked before training)")
    return ser.evaluation_result_dict(result)


@router.post("/{model}/rollback", summary="Roll back to the previous production version (req.md Sec. 26-27, 43)")
def trigger_rollback(model: str, body: schemas.RollbackRequest, db: Session = Depends(get_db)):
    trained_model = _get_model(db, model)
    try:
        event = pe.rollback(db, trained_model, reason=body.reason, triggered_by="manual")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return ser.rollback_event_dict(event)
