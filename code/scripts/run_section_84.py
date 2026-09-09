"""Execute Section 8.4: Retrain iff SIGNIFICANT drift AND EvaluationLevel != GOOD.

EvaluationLevel is F1 of the current champion on the new batch's test split
(GOOD iff F1 >= 0.70). This process does not change the confirmatory API seed.
"""
import json
import logging
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path("/app")))

from app import data_generator as gen
from app.config import settings
from app.ml.drift import drift_level, psi_numeric
from app.ml.evaluation_metrics import classification_metrics
from app.ml.gates import evaluation_gate
from app.ml.pytorch_trainer import best_threshold_for_f1, predict, train_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("section-84")

SCENARIOS = [
    "healthy",
    "volume_anomaly",
    "feature_drift",
    "label_imbalance",
    "regression",
]
SEEDS = [8401, 8402, 8403, 8404, 8405]
F1_GOOD = settings.minimum_f1
OUT = Path("/tmp/section-84.json")


def arrays(records, split):
    return gen.records_to_arrays(records, split)


def feature_cols(records):
    return {
        name: np.array([r[name] for r in records], dtype=float)
        for name in gen.FEATURE_NAMES
    }


def mean_psi(ref_records, prod_records) -> float:
    ref = feature_cols(ref_records)
    prod = feature_cols(prod_records)
    vals = [psi_numeric(ref[n], prod[n]) for n in gen.FEATURE_NAMES]
    return float(np.mean(vals)) if vals else 0.0


def eval_champion(model, threshold, records) -> dict:
    x, y = arrays(records, "test")
    if len(y) < 5:
        return {"f1": None, "level": "UNKNOWN", "n_test": int(len(y))}
    probs = predict(model, x)
    preds = (probs >= threshold).astype(int)
    m = classification_metrics(probs, preds, y)
    level = "GOOD" if m["f1"] >= F1_GOOD else "BAD"
    return {**m, "level": level, "n_test": int(len(y))}


def train(records, seed: int):
    x_tr, y_tr = arrays(records, "train")
    x_va, y_va = arrays(records, "val")
    trained, loss = train_model(
        x_tr, y_tr,
        epochs=settings.train_epochs,
        batch_size=settings.train_batch_size,
        learning_rate=settings.train_learning_rate,
        hidden1=settings.hidden_dim_1,
        hidden2=settings.hidden_dim_2,
        seed=seed % (2**31),
    )
    val_probs = predict(trained, x_va)
    threshold = best_threshold_for_f1(val_probs, y_va) if len(y_va) else 0.5
    x_te, y_te = arrays(records, "test")
    te_probs = predict(trained, x_te)
    te_preds = (te_probs >= threshold).astype(int)
    metrics = classification_metrics(te_probs, te_preds, y_te) if len(y_te) else {}
    return trained, threshold, metrics, loss


def cell(drift: str, ev: str) -> str:
    table = {
        ("NORMAL", "GOOD"): "Continue",
        ("NORMAL", "BAD"): "Investigate model",
        ("NORMAL", "UNKNOWN"): "Continue monitoring",
        ("WARNING", "GOOD"): "Continue",
        ("WARNING", "BAD"): "Investigate model",
        ("WARNING", "UNKNOWN"): "Continue monitoring",
        ("SIGNIFICANT", "GOOD"): "Investigate",
        ("SIGNIFICANT", "BAD"): "Retrain / review",
        ("SIGNIFICANT", "UNKNOWN"): "Obtain ground truth",
    }
    return table.get((drift, ev), "unspecified")


def main() -> None:
    rows = []
    for seed in SEEDS:
        log.info("seed %s: train healthy champion", seed)
        healthy = gen.generate_scenario("healthy", seed, settings.expected_volume)
        champ, thr, champ_metrics, _ = train(healthy, seed)
        for i, scenario in enumerate(SCENARIOS):
            batch = gen.generate_scenario(scenario, seed + 10 * (i + 1), settings.expected_volume)
            psi = round(mean_psi(healthy, batch), 4)
            dlev = drift_level(psi)
            ev = eval_champion(champ, thr, batch)
            elev = ev["level"]
            fire = dlev == "SIGNIFICANT" and elev != "GOOD"
            rec = {
                "seed": seed,
                "scenario": scenario,
                "n_rows": len(batch),
                "psi_mean": psi,
                "drift_level": dlev,
                "champion_f1_on_batch": None if ev["f1"] is None else round(ev["f1"], 4),
                "evaluation_level": elev,
                "matrix_cell": cell(dlev, elev),
                "joint_retrain": fire,
                "candidate": None,
            }
            if fire:
                log.info("  %s: JOINT FIRE psi=%.3f champ_f1=%s → retrain", scenario, psi, ev["f1"])
                cand_model, cand_thr, cand_metrics, _ = train(batch, seed + 100 * (i + 1))
                gate, reg, reasons = evaluation_gate(cand_metrics, champ_metrics)
                rec["candidate"] = {
                    "f1": round(cand_metrics.get("f1", 0), 4),
                    "accuracy": round(cand_metrics.get("accuracy", 0), 4),
                    "gate": gate,
                    "regression_pct": reg,
                    "reasons": reasons,
                }
            else:
                log.info("  %s: no retrain (%s × %s)", scenario, dlev, elev)
            rows.append(rec)
    fires = sum(1 for r in rows if r["joint_retrain"])
    blob = {
        "predicate": "Retrain = (DriftLevel == SIGNIFICANT) and (EvaluationLevel != GOOD)",
        "evaluation_level": "GOOD iff champion F1 on the new test split >= 0.70",
        "n_seeds": len(SEEDS),
        "n_scenario_cells": len(rows),
        "joint_fires": fires,
        "rows": rows,
    }
    OUT.write_text(json.dumps(blob, indent=2) + "\n")
    print(json.dumps({k: blob[k] for k in blob if k != "rows"}, indent=2))
    for r in rows:
        print(
            f"{r['seed']} {r['scenario']:16} PSI={r['psi_mean']:.3f} {r['drift_level']:12} "
            f"F1={r['champion_f1_on_batch']} {r['evaluation_level']:8} "
            f"{'FIRE' if r['joint_retrain'] else 'hold':4} {r['matrix_cell']}"
        )


if __name__ == "__main__":
    main()
