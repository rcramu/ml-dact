"""Exploratory second model family: L2 logistic regression on the same generator.

Same planned order and Algorithm 1 as Table 6. In-process only — does not
touch confirmatory MLP registry names. The generator labels are a linear
logit, so this family is correctly specified relative to the DGP.
"""
import json
import logging
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(Path("/app")))

from app import data_generator as gen
from app.config import settings
from app.ml.drift import drift_level, psi_numeric
from app.ml.evaluation_metrics import classification_metrics
from app.ml.gates import evaluation_gate
from app.ml.pytorch_trainer import best_threshold_for_f1

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("second-family")

SEEDS = [9201, 9202, 9203, 9204, 9205]
PLAN = [
    "healthy",
    "volume_anomaly",
    "feature_drift",
    "label_imbalance",
    "regression",
    "healthy_after_rollback",
]
OUT = Path("/tmp/second-family.json")


def arrays(records, split):
    return gen.records_to_arrays(records, split)


def mean_psi(ref_records, prod_records) -> float:
    ref = {n: np.array([r[n] for r in ref_records], dtype=float) for n in gen.FEATURE_NAMES}
    prod = {n: np.array([r[n] for r in prod_records], dtype=float) for n in gen.FEATURE_NAMES}
    return float(np.mean([psi_numeric(ref[n], prod[n]) for n in gen.FEATURE_NAMES]))


def volume_ok(n: int) -> bool:
    ratio = n / settings.expected_volume
    return (1 - settings.volume_anomaly_tolerance) <= ratio <= (1 + settings.volume_anomaly_tolerance)


def train_lr(records, seed: int):
    x_tr, y_tr = arrays(records, "train")
    x_va, y_va = arrays(records, "val")
    x_te, y_te = arrays(records, "test")
    model = LogisticRegression(
        max_iter=500,
        class_weight="balanced",
        solver="lbfgs",
        random_state=int(seed) % (2**31),
    )
    model.fit(x_tr, y_tr)
    val_probs = model.predict_proba(x_va)[:, 1] if len(y_va) else np.array([])
    threshold = best_threshold_for_f1(val_probs, y_va) if len(y_va) else 0.5
    te_probs = model.predict_proba(x_te)[:, 1] if len(y_te) else np.array([])
    te_preds = (te_probs >= threshold).astype(int) if len(y_te) else np.array([])
    metrics = classification_metrics(te_probs, te_preds, y_te) if len(y_te) else {}
    return model, threshold, metrics


def decide(metrics, champion_metrics):
    gate, reg, reasons = evaluation_gate(metrics, champion_metrics)
    return ("PROMOTED" if gate == "PASS" else "REJECTED"), reg, reasons


def main() -> None:
    rows = []
    for seed in SEEDS:
        log.info("seed %s", seed)
        healthy_ref = None
        champion = None
        first_champion = None
        for i, scenario in enumerate(PLAN):
            gen_name = "healthy" if scenario == "healthy_after_rollback" else scenario
            batch = gen.generate_scenario(gen_name, seed + 17 * (i + 1), settings.expected_volume)
            if healthy_ref is None:
                healthy_ref = batch
            rec = {
                "seed": seed,
                "scenario": scenario,
                "n_rows": len(batch),
                "psi_mean": round(mean_psi(healthy_ref, batch), 4),
                "drift_level": drift_level(mean_psi(healthy_ref, batch)),
                "outcome": None,
                "f1": None,
                "accuracy": None,
                "regression_pct": None,
                "reasons": None,
            }
            if not volume_ok(len(batch)):
                rec["outcome"] = "BLOCKED"
                log.info("  %s BLOCKED n=%s", scenario, len(batch))
                rows.append(rec)
                continue
            _model, _thr, metrics = train_lr(batch, seed + 100 * (i + 1))
            outcome, reg, reasons = decide(metrics, champion)
            rec.update({
                "outcome": outcome,
                "f1": round(metrics.get("f1", 0), 4),
                "accuracy": round(metrics.get("accuracy", 0), 4),
                "precision": round(metrics.get("precision", 0), 4),
                "recall": round(metrics.get("recall", 0), 4),
                "regression_pct": reg,
                "reasons": reasons,
            })
            if outcome == "PROMOTED":
                champion = metrics
                if first_champion is None:
                    first_champion = metrics
            if scenario == "regression":
                champion = first_champion
                rec["rollback_simulated"] = True
            log.info("  %s %s F1=%s PSI=%s", scenario, rec["outcome"], rec["f1"], rec["psi_mean"])
            rows.append(rec)

    by = {}
    for r in rows:
        by.setdefault(r["scenario"], []).append(r)
    summary = {}
    for scenario, items in by.items():
        summary[scenario] = {
            "outcomes": {k: sum(1 for r in items if r["outcome"] == k) for k in ("PROMOTED", "REJECTED", "BLOCKED")},
            "mean_f1": round(float(np.mean([r["f1"] for r in items if r["f1"] is not None])), 4)
            if any(r["f1"] is not None for r in items) else None,
            "mean_psi": round(float(np.mean([r["psi_mean"] for r in items])), 4),
        }
    blob = {
        "family": "sklearn LogisticRegression (L2, class_weight=balanced)",
        "note": "Same generator and Algorithm 1 as Table 6. Exploratory; not used to rescore H1-H3. Labels are a linear logit, so LR is correctly specified.",
        "n_seeds": len(SEEDS),
        "n_runs": len(rows),
        "summary": summary,
        "rows": rows,
    }
    OUT.write_text(json.dumps(blob, indent=2) + "\n")
    print(json.dumps({"summary": summary, "n_runs": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
