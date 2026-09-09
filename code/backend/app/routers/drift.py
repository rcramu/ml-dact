"""Drift monitoring API - computes PSI/KS (paper Section 8) between the
model's original baseline ("healthy") dataset and every subsequent dataset
version ingested by the pipeline. This is what the paper's Section 5
"Monitoring & Drift Detection" layer and Section 6.1 closed loop refer to.
"""
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import data_generator as gen
from .. import models as m
from ..database import get_db
from ..ml import drift as drift_stats

router = APIRouter(prefix="/api/v1/models", tags=["Drift Monitoring"])

PSI_WARNING = 0.10
PSI_CRITICAL = 0.25


def _get_model(db: Session, name: str) -> m.TrainedModel:
    model = db.query(m.TrainedModel).filter_by(name=name).one_or_none()
    if model is None:
        raise HTTPException(404, f"model '{name}' not found")
    return model


def _feature_matrix(db: Session, dataset_version_id: str) -> dict:
    rows = db.query(m.RawRecord).filter_by(dataset_version_id=dataset_version_id).all()
    return {
        name: np.array([getattr(r, name) for r in rows], dtype=float)
        for name in gen.FEATURE_NAMES
    }


def _compare(db: Session, reference_id: str, production_id: str) -> dict:
    ref = _feature_matrix(db, reference_id)
    prod = _feature_matrix(db, production_id)
    per_feature = []
    psi_values = []
    for name in gen.FEATURE_NAMES:
        psi = drift_stats.psi_numeric(ref[name], prod[name])
        ks_stat, ks_p = drift_stats.ks_test(ref[name], prod[name])
        psi_values.append(psi)
        per_feature.append({
            "feature": name,
            "psi": round(psi, 4),
            "ks_statistic": round(ks_stat, 4),
            "ks_p_value": round(ks_p, 4),
            "reference_mean": round(float(ref[name].mean()) if len(ref[name]) else 0.0, 4),
            "production_mean": round(float(prod[name].mean()) if len(prod[name]) else 0.0, 4),
            "drift_level": drift_stats.drift_level(psi, PSI_WARNING, PSI_CRITICAL),
        })
    overall_psi = float(np.mean(psi_values)) if psi_values else 0.0
    return {
        "reference_dataset_version_id": reference_id,
        "production_dataset_version_id": production_id,
        "psi_overall": round(overall_psi, 4),
        "drift_level": drift_stats.drift_level(overall_psi, PSI_WARNING, PSI_CRITICAL),
        "thresholds": {"warning": PSI_WARNING, "critical": PSI_CRITICAL},
        "features": per_feature,
    }


@router.get("/{model}/drift", summary="Current drift status: reference (first healthy dataset) vs. latest ingested dataset")
def current_drift(model: str, db: Session = Depends(get_db)):
    trained_model = _get_model(db, model)
    datasets = (
        db.query(m.DatasetVersion).filter_by(model_id=trained_model.id)
        .order_by(m.DatasetVersion.created_at.asc()).all()
    )
    if not datasets:
        raise HTTPException(404, "no ingested datasets yet for this model")
    reference = next((d for d in datasets if d.scenario == "healthy"), datasets[0])
    latest = datasets[-1]
    return _compare(db, reference.id, latest.id)


@router.get("/{model}/drift/history", summary="PSI trend across every ingested dataset version vs. the reference baseline")
def drift_history(model: str, db: Session = Depends(get_db)):
    trained_model = _get_model(db, model)
    datasets = (
        db.query(m.DatasetVersion).filter_by(model_id=trained_model.id)
        .order_by(m.DatasetVersion.created_at.asc()).all()
    )
    if not datasets:
        raise HTTPException(404, "no ingested datasets yet for this model")
    reference = next((d for d in datasets if d.scenario == "healthy"), datasets[0])
    history = []
    for d in datasets:
        result = _compare(db, reference.id, d.id)
        history.append({
            "dataset_version_id": d.id,
            "scenario": d.scenario,
            "created_at": d.created_at.isoformat(),
            "psi_overall": result["psi_overall"],
            "drift_level": result["drift_level"],
        })
    return {"reference_dataset_version_id": reference.id, "history": history}
