"""Model & version registry — champion/challenger visibility (req.md Sec. 18-19, 43)."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models as m
from .. import serializers as ser
from ..database import get_db

router = APIRouter(prefix="/api/v1/models", tags=["Models & Registry"])


@router.get("", summary="List every model, its current champion, and fleet-wide counts")
def list_models(db: Session = Depends(get_db)):
    out = []
    for model in db.query(m.TrainedModel).order_by(m.TrainedModel.name).all():
        champion = db.query(m.ModelVersion).filter_by(model_id=model.id, is_champion=True).one_or_none()
        version_count = db.query(m.ModelVersion).filter_by(model_id=model.id).count()
        run_count = db.query(m.PipelineRun).filter_by(model_id=model.id).count()
        d = ser.model_dict(model)
        d["champion"] = ser.model_version_dict(champion) if champion else None
        d["version_count"] = version_count
        d["run_count"] = run_count
        out.append(d)
    return out


@router.get("/{model}/versions", summary="All versions for a model — champion, archived, rejected, rolled back")
def list_versions(model: str, db: Session = Depends(get_db), limit: int = Query(100, le=500)):
    trained_model = db.query(m.TrainedModel).filter_by(name=model).one_or_none()
    if trained_model is None:
        raise HTTPException(404, f"model '{model}' not found")
    rows = (
        db.query(m.ModelVersion).filter_by(model_id=trained_model.id)
        .order_by(m.ModelVersion.version.desc()).limit(limit).all()
    )
    return [ser.model_version_dict(v) for v in rows]


@router.get("/{model}/deployment", summary="Deployment/canary + rollback timeline for a model's current & recent versions")
def deployment_timeline(model: str, db: Session = Depends(get_db)):
    trained_model = db.query(m.TrainedModel).filter_by(name=model).one_or_none()
    if trained_model is None:
        raise HTTPException(404, f"model '{model}' not found")
    versions = db.query(m.ModelVersion).filter_by(model_id=trained_model.id).all()
    version_number_by_id = {v.id: v.version for v in versions}
    version_ids = list(version_number_by_id.keys())
    events = (
        db.query(m.DeploymentEvent).filter(m.DeploymentEvent.model_version_id.in_(version_ids))
        .order_by(m.DeploymentEvent.created_at.desc()).limit(100).all()
    ) if version_ids else []
    rollbacks = (
        db.query(m.RollbackEvent).filter_by(model_id=trained_model.id)
        .order_by(m.RollbackEvent.created_at.desc()).all()
    )
    return {
        "events": [ser.deployment_event_dict(e) for e in events],
        "rollbacks": [
            {**ser.rollback_event_dict(r),
             "from_version": version_number_by_id.get(r.from_version_id),
             "to_version": version_number_by_id.get(r.to_version_id)}
            for r in rollbacks
        ],
    }
    return {
        "events": [ser.deployment_event_dict(e) for e in events],
        "rollbacks": [ser.rollback_event_dict(r) for r in rollbacks],
    }
