"""Startup bootstrap - seeds the flagship model + runs a representative set of
pipeline runs so `docker compose up` alone reproduces the paper's experimental
narrative (Sections 7 and 11-13): a healthy baseline promotion, a blocked
data-volume anomaly, a drift-triggered promotion (Experiment 3, recovering
performance after Experiment 2's induced drift), a data-quality-warning
rejection, a regression rejection, and one automatic rollback.
"""
import logging

from sqlalchemy.orm import Session

from . import models as m
from . import pipeline_engine as pe
from .database import Base, SessionLocal, engine

logger = logging.getLogger("continuoustraining.seed")

FLEET_SPEC = [
    {"name": "churn-predictor", "task_type": "classification", "owner": "retention-ml",
     "description": (
         "Predicts customer churn risk from the synthetic churn dataset described in the paper's "
         "Section 7.1; the flagship model exercising the closed-loop drift-aware continuous "
         "training architecture (Section 5)."
     )},
]

# (trigger_type, trigger_detail, scenario) - mirrors the paper's Experiments 1-3 (Section 7.2)
# plus two additional operational triggers (data-volume anomaly, class imbalance) that exercise
# the quality gate (Section 9) beyond pure drift.
CHURN_RUN_PLAN = [
    ("schedule", "Weekly scheduled retraining (cron 0 2 * * 0) - Experiment 1: baseline", "healthy"),
    ("data_availability", "1,000,000 new labeled records available (simulated volume anomaly)", "volume_anomaly"),
    ("drift", "Feature drift detected by the Drift Monitoring tab: PSI=0.81 on customer_satisfaction/usage_score - Experiment 2/3: drift then automated retraining", "feature_drift"),
    ("schedule", "Weekly scheduled retraining (cron 0 2 * * 0)", "label_imbalance"),
    ("performance", "Production F1 dipped below 0.85 - investigating with a larger labeled sample", "regression"),
]


def bootstrap() -> None:
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        if db.query(m.TrainedModel).count() > 0:
            logger.info("Database already seeded - skipping bootstrap")
            return

        pe.ensure_sla_config(db)

        for spec in FLEET_SPEC:
            model = m.TrainedModel(name=spec["name"], task_type=spec["task_type"],
                                    owner_team=spec["owner"], description=spec["description"])
            db.add(model)
            db.flush()

            for trigger_type, trigger_detail, scenario in CHURN_RUN_PLAN:
                pe.run_pipeline(db, model, trigger_type=trigger_type, trigger_detail=trigger_detail, scenario=scenario)

        # Demonstrate an automatic rollback: after the drift-triggered promotion becomes champion,
        # simulate the monitoring stack detecting a production regression and rolling back
        # automatically (Section 6.1's closed loop, Figure 2's control/trigger path).
        churn_model = db.query(m.TrainedModel).filter_by(name="churn-predictor").one()
        try:
            pe.rollback(db, churn_model,
                        reason="Production regression detected: live F1 dropped to 0.79 on the last 6h of traffic",
                        triggered_by="automatic")
        except ValueError as exc:
            logger.warning("Seed rollback skipped: %s", exc)

        # Re-run once more after the rollback with a fresh healthy dataset. Depending on natural
        # sampling variance this either promotes a new, better champion or is correctly rejected by
        # the evaluation gate (keeping the reliable rolled-back-to champion in production) - both
        # outcomes are valid demonstrations of the gate protecting production quality (Section 9).
        pe.run_pipeline(db, churn_model, trigger_type="manual",
                         trigger_detail="Re-run after rollback with a corrected dataset", scenario="healthy")

        logger.info("Bootstrap complete: %d model(s) seeded", len(FLEET_SPEC))
    finally:
        db.close()
