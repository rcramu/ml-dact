"""Create exploratory joint models and install a healthy champion.

New names only. Does not touch churn-predictor or r2-r5.
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path("/app")))

from app import models as m
from app import pipeline_engine as pe
from app.database import SessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("setup-joint")

MODELS = [f"churn-predictor-joint{i}" for i in range(1, 6)]
SEEDS = [9801, 9802, 9803, 9804, 9805]


def main() -> None:
    db = SessionLocal()
    try:
        pe.ensure_sla_config(db)
        for name, seed in zip(MODELS, SEEDS):
            model = db.query(m.TrainedModel).filter_by(name=name).one_or_none()
            if model is None:
                model = m.TrainedModel(
                    name=name,
                    task_type="classification",
                    owner_team="retention-ml",
                    description="Exploratory live Airflow joint-cell model. Not confirmatory.",
                )
                db.add(model)
                db.flush()
            n_runs = db.query(m.PipelineRun).filter_by(model_id=model.id).count()
            champ = db.query(m.ModelVersion).filter_by(model_id=model.id, is_champion=True).one_or_none()
            if champ is not None:
                log.info("skip %s — champion already installed", name)
                continue
            log.info("healthy train %s seed=%s (prior runs=%s)", name, seed, n_runs)
            pe.run_pipeline(
                db, model,
                trigger_type="manual",
                trigger_detail=f"joint-cell healthy opener seed={seed}",
                scenario="healthy",
            )
        log.info("setup complete")
    finally:
        db.close()


if __name__ == "__main__":
    main()
