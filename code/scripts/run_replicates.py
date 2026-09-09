"""Run independent copies of the paper seed plan (new model names)."""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path("/app")))

from app import models as m
from app import pipeline_engine as pe
from app.database import SessionLocal
from app.seed import CHURN_RUN_PLAN

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("replicates")

REPLICATES = [
    "churn-predictor-r2",
    "churn-predictor-r3",
    "churn-predictor-r4",
    "churn-predictor-r5",
]


def main() -> None:
    db = SessionLocal()
    try:
        pe.ensure_sla_config(db)
        for name in REPLICATES:
            existing = db.query(m.TrainedModel).filter_by(name=name).one_or_none()
            if existing is not None and db.query(m.PipelineRun).filter_by(model_id=existing.id).count() >= 6:
                log.info("skip %s — already has runs", name)
                continue
            if existing is None:
                model = m.TrainedModel(
                    name=name,
                    task_type="classification",
                    owner_team="retention-ml",
                    description=f"Independent replicate of the Section 11 seed protocol ({name}).",
                )
                db.add(model)
                db.flush()
            else:
                model = existing
            log.info("starting seed plan for %s", name)
            for trigger_type, trigger_detail, scenario in CHURN_RUN_PLAN:
                log.info("  %s / %s", trigger_type, scenario)
                pe.run_pipeline(
                    db, model,
                    trigger_type=trigger_type,
                    trigger_detail=f"{trigger_detail} [{name}]",
                    scenario=scenario,
                )
            try:
                pe.rollback(
                    db, model,
                    reason="Replicate seed: simulated production F1 dip, restore prior champion",
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
        log.info("all replicates complete")
    finally:
        db.close()


if __name__ == "__main__":
    main()
