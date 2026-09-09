"""Register the exploratory Electricity joint-cell model.

Does not touch churn-predictor or r2-r5. Does not train.
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path("/app")))

from app import models as m
from app import pipeline_engine as pe
from app.database import SessionLocal
from app.ml.electricity import MODEL_NAME

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("setup-electricity")


def main() -> None:
    db = SessionLocal()
    try:
        pe.ensure_sla_config(db)
        model = db.query(m.TrainedModel).filter_by(name=MODEL_NAME).one_or_none()
        if model is None:
            model = m.TrainedModel(
                name=MODEL_NAME,
                task_type="classification",
                owner_team="energy-ml",
                description="Exploratory Electricity (Elec2) live Airflow joint-cell model. Not confirmatory.",
            )
            db.add(model)
            db.commit()
            log.info("created %s", MODEL_NAME)
        else:
            log.info("exists %s", MODEL_NAME)
    finally:
        db.close()


if __name__ == "__main__":
    main()
