"""Per-feature PSI/KS for confirmatory seeds: first healthy vs feature_drift."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path("/app")))

from app import models as m
from app.database import SessionLocal
from app.routers.drift import _compare

MODELS = [
    "churn-predictor",
    "churn-predictor-r2",
    "churn-predictor-r3",
    "churn-predictor-r4",
    "churn-predictor-r5",
]
INJECTED = {"usage_score", "customer_satisfaction"}


def main() -> None:
    db = SessionLocal()
    rows = []
    try:
        for name in MODELS:
            model = db.query(m.TrainedModel).filter_by(name=name).one()
            datasets = (
                db.query(m.DatasetVersion)
                .filter_by(model_id=model.id)
                .order_by(m.DatasetVersion.created_at.asc())
                .all()
            )
            reference = next(d for d in datasets if d.scenario == "healthy")
            drifted = next(d for d in datasets if d.scenario == "feature_drift")
            result = _compare(db, reference.id, drifted.id)
            inj = [f for f in result["features"] if f["feature"] in INJECTED]
            other = [f for f in result["features"] if f["feature"] not in INJECTED]
            rows.append(
                {
                    "model": name,
                    "psi_overall": result["psi_overall"],
                    "drift_level": result["drift_level"],
                    "injected": inj,
                    "other_max_psi": max(f["psi"] for f in other),
                    "other_significant": [f["feature"] for f in other if f["drift_level"] == "SIGNIFICANT"],
                    "other_warning": [f["feature"] for f in other if f["drift_level"] == "WARNING"],
                    "features": result["features"],
                }
            )
    finally:
        db.close()
    print(json.dumps({"n": len(rows), "rows": rows}, indent=2))


if __name__ == "__main__":
    main()
