"""Live gate ablation: same planned order, new model names, swapped gate.

Does not touch churn-predictor / r2–r5 (full Algorithm 1). This process
monkeypatches evaluation_gate so promotions are real registry events.
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path("/app")))

from app import models as m
from app import pipeline_engine as pe
from app.database import SessionLocal
from app.ml import gates
from app.seed import CHURN_RUN_PLAN

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("live-ablation")

ACC_MIN = 0.70
F1_MIN, P_MIN, R_MIN = 0.70, 0.60, 0.60


def accuracy_only_gate(candidate: dict, champion: dict | None):
    acc = candidate.get("accuracy", 0.0)
    if acc < ACC_MIN:
        return "FAIL", None, f"accuracy-only: accuracy {acc:.3f} below {ACC_MIN:.2f}"
    return "PASS", None, f"accuracy-only: accuracy {acc:.3f} >= {ACC_MIN:.2f} (champion ignored)"


def floors_only_gate(candidate: dict, champion: dict | None):
    reasons = []
    if candidate["f1"] < F1_MIN:
        reasons.append(f"F1 {candidate['f1']:.3f} < {F1_MIN:.2f}")
    if candidate["recall"] < R_MIN:
        reasons.append(f"recall {candidate['recall']:.3f} < {R_MIN:.2f}")
    if candidate["precision"] < P_MIN:
        reasons.append(f"precision {candidate['precision']:.3f} < {P_MIN:.2f}")
    if reasons:
        return "FAIL", None, "floors-only: " + "; ".join(reasons)
    return "PASS", None, "floors-only: F1/P/R minima met (no regression budget, no recall-vs-champion)"


ARMS = {
    "accuracy_only": {
        "gate": accuracy_only_gate,
        "models": [f"churn-predictor-acc{i}" for i in range(1, 6)],
    },
    "floors_only": {
        "gate": floors_only_gate,
        "models": [f"churn-predictor-floors{i}" for i in range(1, 6)],
    },
}


def run_one(db, name: str, arm: str) -> None:
    existing = db.query(m.TrainedModel).filter_by(name=name).one_or_none()
    if existing is not None and db.query(m.PipelineRun).filter_by(model_id=existing.id).count() >= 6:
        log.info("skip %s — already has runs", name)
        return
    if existing is None:
        model = m.TrainedModel(
            name=name,
            task_type="classification",
            owner_team="retention-ml",
            description=f"Live ablation ({arm}) of the Section 11 seed protocol",
        )
        db.add(model)
        db.flush()
    else:
        model = existing
    log.info("starting %s arm=%s", name, arm)
    for trigger_type, trigger_detail, scenario in CHURN_RUN_PLAN:
        log.info("  %s / %s", trigger_type, scenario)
        pe.run_pipeline(
            db, model,
            trigger_type=trigger_type,
            trigger_detail=f"{trigger_detail} [{name} {arm}]",
            scenario=scenario,
        )
    try:
        pe.rollback(
            db, model,
            reason=f"Live ablation ({arm}): simulated production F1 dip",
            triggered_by="automatic",
        )
        log.info("  rollback ok")
    except ValueError as exc:
        log.warning("  rollback skipped: %s", exc)
    pe.run_pipeline(
        db, model,
        trigger_type="manual",
        trigger_detail=f"Re-run after rollback [{name} {arm}]",
        scenario="healthy",
    )
    log.info("finished %s", name)


def main() -> None:
    db = SessionLocal()
    try:
        pe.ensure_sla_config(db)
        for arm, spec in ARMS.items():
            gates.evaluation_gate = spec["gate"]
            log.info("gate patched to %s", arm)
            for name in spec["models"]:
                run_one(db, name, arm)
        log.info("all live ablation replicates complete")
    finally:
        db.close()


if __name__ == "__main__":
    main()
