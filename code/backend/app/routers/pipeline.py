"""Cross-model pipeline run visibility + SLA dashboard (req.md Sec. 9-10, 28-29)."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models as m
from .. import serializers as ser
from ..database import get_db
from ..pipeline_engine import SLA_DEFAULTS

router = APIRouter(prefix="/pipeline", tags=["Pipeline Runs"])


@router.get("/runs", summary="List pipeline runs across every model (Airflow + manual + startup)")
def list_runs(db: Session = Depends(get_db), model_id: str | None = None, status: str | None = None, limit: int = Query(50, le=200)):
    q = db.query(m.PipelineRun)
    if model_id:
        q = q.filter(m.PipelineRun.model_id == model_id)
    if status:
        q = q.filter(m.PipelineRun.status == status.upper())
    rows = q.order_by(m.PipelineRun.started_at.desc()).limit(limit).all()
    out = []
    for r in rows:
        d = ser.pipeline_run_dict(r)
        d["model_name"] = r.model.name
        out.append(d)
    return out


@router.get("/runs/{run_id}", summary="Pipeline run detail — every one of the 16 DAG stages (req.md Sec. 10)")
def run_detail(run_id: str, db: Session = Depends(get_db)):
    run = db.query(m.PipelineRun).filter_by(id=run_id).one_or_none()
    if run is None:
        raise HTTPException(404, "pipeline run not found")
    d = ser.pipeline_run_dict(run, include_stages=True)
    d["model_name"] = run.model.name
    return d


@router.get("/sla", summary="SLA thresholds + violations across every run (req.md Sec. 28-29)")
def sla_dashboard(db: Session = Depends(get_db), limit: int = Query(50, le=200)):
    configs = db.query(m.SlaConfig).order_by(m.SlaConfig.stage_name).all()
    violations = db.query(m.SlaViolation).order_by(m.SlaViolation.created_at.desc()).limit(limit).all()
    total_runs = db.query(m.PipelineRun).count()
    runs_with_violation = db.query(m.SlaViolation.run_id).distinct().count()
    return {
        "stage_thresholds": {c.stage_name: c.max_minutes for c in configs} or SLA_DEFAULTS,
        "violations": [ser.sla_violation_dict(v) for v in violations],
        "compliance_pct": round(100 * (1 - (runs_with_violation / total_runs)), 1) if total_runs else 100.0,
        "total_runs": total_runs,
        "runs_with_violation": runs_with_violation,
    }
