"""Browse every ingested/derived table (req.md Sec. 12, 28 "show the ingested data")."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from .. import serializers as ser

router = APIRouter(prefix="/data", tags=["Ingested Data"])


@router.get("/summary", summary="Ingestion counts across every table")
def summary(db: Session = Depends(get_db)):
    return {
        "models_count": db.query(models.TrainedModel).count(),
        "dataset_versions_count": db.query(models.DatasetVersion).count(),
        "raw_records_count": db.query(models.RawRecord).count(),
        "model_versions_count": db.query(models.ModelVersion).count(),
        "pipeline_runs_count": db.query(models.PipelineRun).count(),
        "evaluation_results_count": db.query(models.EvaluationResult).count(),
        "deployment_events_count": db.query(models.DeploymentEvent).count(),
        "rollback_events_count": db.query(models.RollbackEvent).count(),
        "alerts_count": db.query(models.Alert).count(),
        "audit_logs_count": db.query(models.AuditLog).count(),
    }


@router.get("/datasets", summary="Browse seeded dataset versions")
def list_datasets(db: Session = Depends(get_db), model_id: str | None = None, limit: int = Query(100, le=500)):
    q = db.query(models.DatasetVersion)
    if model_id:
        q = q.filter(models.DatasetVersion.model_id == model_id)
    rows = q.order_by(models.DatasetVersion.created_at.desc()).limit(limit).all()
    return [ser.dataset_version_dict(d) for d in rows]


@router.get("/records", summary="Browse ingested raw synthetic transaction records (the training data itself)")
def list_records(db: Session = Depends(get_db), dataset_version_id: str | None = None, split: str | None = None, limit: int = Query(100, le=1000)):
    q = db.query(models.RawRecord)
    if dataset_version_id:
        q = q.filter(models.RawRecord.dataset_version_id == dataset_version_id)
    if split:
        q = q.filter(models.RawRecord.split == split)
    rows = q.order_by(models.RawRecord.created_at.desc()).limit(limit).all()
    return [ser.raw_record_dict(r) for r in rows]


@router.get("/data-quality-checks", summary="Browse data-quality gate results (req.md Sec. 32)")
def list_dq_checks(db: Session = Depends(get_db), dataset_version_id: str | None = None, limit: int = Query(100, le=500)):
    q = db.query(models.DataQualityCheck)
    if dataset_version_id:
        q = q.filter(models.DataQualityCheck.dataset_version_id == dataset_version_id)
    rows = q.order_by(models.DataQualityCheck.id.desc()).limit(limit).all()
    return [ser.data_quality_check_dict(c) for c in rows]


@router.get("/audit-log", summary="Governance / audit trail (req.md Sec. 48)")
def list_audit_log(db: Session = Depends(get_db), limit: int = Query(100, le=500)):
    rows = db.query(models.AuditLog).order_by(models.AuditLog.created_at.desc()).limit(limit).all()
    return [ser.audit_log_dict(a) for a in rows]


@router.get("/seed-scenarios", summary="List the 5 seedable data scenarios (req.md Sec. 13)")
def seed_scenarios():
    return {
        "scenarios": [
            {"id": "healthy", "expected_outcome": "TRAINING_ALLOWED", "description": "~900 rows, <1% missing, matches baseline distribution."},
            {"id": "volume_anomaly", "expected_outcome": "TRAINING_BLOCKED / DATA_VOLUME_ALERT", "description": "Only ~12% of the expected row count is generated."},
            {"id": "feature_drift", "expected_outcome": "RETRAIN_TRIGGERED", "description": "customer_satisfaction and service_count distributions shift meaningfully."},
            {"id": "label_imbalance", "expected_outcome": "DATA_QUALITY_WARNING", "description": "Churn ratio forced down to ~2% of records."},
            {"id": "regression", "expected_outcome": "EVALUATION_GATE = FAIL / MODEL_NOT_PROMOTED", "description": "Heavy label noise so the trained candidate underperforms the champion."},
        ]
    }
