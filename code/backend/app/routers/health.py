"""Liveness/readiness probes for docker-compose and Kubernetes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Liveness probe")
def health():
    return {"status": "ok"}


@router.get("/ready", summary="Readiness probe — DB connectivity + fleet seeding status")
def ready(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    models_count = db.query(models.TrainedModel).count()
    versions_count = db.query(models.ModelVersion).count()
    runs_count = db.query(models.PipelineRun).count()
    payload = {
        "database": True,
        "models_seeded": models_count,
        "versions_seeded": versions_count,
        "pipeline_runs_seeded": runs_count,
        "ready": models_count > 0 and runs_count > 0,
    }
    if not payload["ready"]:
        raise HTTPException(status_code=503, detail=payload)
    return payload
