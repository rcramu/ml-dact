"""Science upgrade 1: same six-run protocol with shuffled stress-scenario order.

The published five-seed study used a fixed order
(healthy → volume_anomaly → feature_drift → label_imbalance → regression
→ rollback → healthy). Gate comparisons after a drift promotion therefore
always saw the high-F1 drift champion. This runner keeps a healthy opener
(so PSI has a reference and the gate has a first champion) and a rollback
coda, and permutes only the four stress scenarios.

New model names — does not overwrite churn-predictor / r2–r5.
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path("/app")))

from app import models as m
from app import pipeline_engine as pe
from app.database import SessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("randomized-order")

STRESS = {
    "volume_anomaly": (
        "data_availability",
        "1,000,000 new labeled records available (simulated volume anomaly)",
    ),
    "feature_drift": (
        "drift",
        "Feature drift detected by the Drift Monitoring tab",
    ),
    "label_imbalance": (
        "schedule",
        "Weekly scheduled retraining (cron 0 2 * * 0)",
    ),
    "regression": (
        "performance",
        "Production F1 dipped below 0.85 - investigating with a larger labeled sample",
    ),
}

# Planned-order confound check. Arm A: imbalance/regression after drift.
# Arm B: imbalance/regression before drift (healthy champion). Target n=10/arm.
ORDERS = {
    # Arm A (existing)
    "churn-predictor-ord1": ["volume_anomaly", "feature_drift", "label_imbalance", "regression"],
    "churn-predictor-ord2": ["feature_drift", "volume_anomaly", "regression", "label_imbalance"],
    "churn-predictor-ord5": ["feature_drift", "regression", "label_imbalance", "volume_anomaly"],
    # Arm A (expansion to n=10)
    "churn-predictor-a4": ["volume_anomaly", "feature_drift", "regression", "label_imbalance"],
    "churn-predictor-a5": ["feature_drift", "volume_anomaly", "label_imbalance", "regression"],
    "churn-predictor-a6": ["feature_drift", "label_imbalance", "regression", "volume_anomaly"],
    "churn-predictor-a7": ["feature_drift", "label_imbalance", "volume_anomaly", "regression"],
    "churn-predictor-a8": ["volume_anomaly", "feature_drift", "label_imbalance", "regression"],
    "churn-predictor-a9": ["feature_drift", "regression", "volume_anomaly", "label_imbalance"],
    "churn-predictor-a10": ["feature_drift", "volume_anomaly", "regression", "label_imbalance"],
    # Arm B (existing)
    "churn-predictor-ord3": ["regression", "label_imbalance", "volume_anomaly", "feature_drift"],
    "churn-predictor-ord4": ["label_imbalance", "regression", "feature_drift", "volume_anomaly"],
    # Arm B (expansion to n=10)
    "churn-predictor-b3": ["regression", "label_imbalance", "feature_drift", "volume_anomaly"],
    "churn-predictor-b4": ["label_imbalance", "regression", "volume_anomaly", "feature_drift"],
    "churn-predictor-b5": ["regression", "volume_anomaly", "label_imbalance", "feature_drift"],
    "churn-predictor-b6": ["label_imbalance", "volume_anomaly", "regression", "feature_drift"],
    "churn-predictor-b7": ["volume_anomaly", "regression", "label_imbalance", "feature_drift"],
    "churn-predictor-b8": ["volume_anomaly", "label_imbalance", "regression", "feature_drift"],
    "churn-predictor-b9": ["regression", "label_imbalance", "volume_anomaly", "feature_drift"],
    "churn-predictor-b10": ["label_imbalance", "regression", "feature_drift", "volume_anomaly"],
}


def run_one(db, name: str, stress_order: list[str]) -> None:
    existing = db.query(m.TrainedModel).filter_by(name=name).one_or_none()
    if existing is not None and db.query(m.PipelineRun).filter_by(model_id=existing.id).count() >= 6:
        log.info("skip %s — already has runs", name)
        return
    if existing is None:
        model = m.TrainedModel(
            name=name,
            task_type="classification",
            owner_team="retention-ml",
            description=f"Randomized-order science upgrade ({name}): {','.join(stress_order)}",
        )
        db.add(model)
        db.flush()
    else:
        model = existing

    log.info("starting %s order=%s", name, stress_order)
    pe.run_pipeline(
        db, model,
        trigger_type="schedule",
        trigger_detail=f"Baseline healthy opener [{name}]",
        scenario="healthy",
    )
    for scenario in stress_order:
        trigger_type, detail = STRESS[scenario]
        log.info("  %s / %s", trigger_type, scenario)
        pe.run_pipeline(
            db, model,
            trigger_type=trigger_type,
            trigger_detail=f"{detail} [{name}]",
            scenario=scenario,
        )
    try:
        pe.rollback(
            db, model,
            reason="Randomized-order seed: simulated production F1 dip, restore prior champion",
            triggered_by="automatic",
        )
        log.info("  rollback ok")
    except ValueError as exc:
        log.warning("  rollback skipped: %s", exc)
    pe.run_pipeline(
        db, model,
        trigger_type="manual",
        trigger_detail=f"Re-run after rollback [{name}]",
        scenario="healthy",
    )
    log.info("finished %s", name)


def main() -> None:
    db = SessionLocal()
    try:
        pe.ensure_sla_config(db)
        for name, order in ORDERS.items():
            run_one(db, name, order)
        log.info("all randomized-order replicates complete")
    finally:
        db.close()


if __name__ == "__main__":
    main()
