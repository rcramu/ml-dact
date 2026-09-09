"""Exploratory public-corpus transfer: IBM Telco churn + protocol perturbations.

The public table is real. Scenario shifts (volume, feature drift, imbalance,
label noise) are ours, not naturally occurring drift. Logistic regression,
Algorithm 1, planned order. In-process only.
"""
import csv
import json
import logging
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(Path("/app")))

from app.config import settings
from app.ml.drift import drift_level, psi_numeric
from app.ml.evaluation_metrics import classification_metrics
from app.ml.gates import evaluation_gate
from app.ml.pytorch_trainer import best_threshold_for_f1

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("telco-transfer")

CSV_CANDIDATES = [
    Path("/tmp/ibm-telco-churn.csv"),
    Path("/app/data/ibm-telco-churn.csv"),
    Path(__file__).resolve().parents[1] / "data" / "ibm-telco-churn.csv",
]
SEEDS = [9301, 9302, 9303, 9304, 9305]
PLAN = [
    "healthy",
    "volume_anomaly",
    "feature_drift",
    "label_imbalance",
    "regression",
    "healthy_after_rollback",
]
FEATURE_NAMES = [
    "senior_citizen",
    "tenure",
    "monthly_charges",
    "total_charges",
    "partner",
    "dependents",
    "paperless",
    "phone",
    "month_to_month",
]
N_TARGET = 1500
OUT = Path("/tmp/telco-transfer.json")


def _yes(value: str) -> float:
    return 1.0 if str(value).strip().lower() == "yes" else 0.0


def load_telco(path: Path) -> dict:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    n = len(rows)
    senior = np.array([float(r["SeniorCitizen"]) for r in rows], dtype=float)
    tenure = np.array([float(r["tenure"]) for r in rows], dtype=float)
    monthly = np.array([float(r["MonthlyCharges"]) for r in rows], dtype=float)
    total = np.array([
        float(r["TotalCharges"]) if str(r["TotalCharges"]).strip() else 0.0
        for r in rows
    ], dtype=float)
    partner = np.array([_yes(r["Partner"]) for r in rows], dtype=float)
    dependents = np.array([_yes(r["Dependents"]) for r in rows], dtype=float)
    paperless = np.array([_yes(r["PaperlessBilling"]) for r in rows], dtype=float)
    phone = np.array([_yes(r["PhoneService"]) for r in rows], dtype=float)
    month = np.array([
        1.0 if r["Contract"].strip() == "Month-to-month" else 0.0 for r in rows
    ], dtype=float)
    y = np.array([_yes(r["Churn"]) for r in rows], dtype=int)
    x = np.stack([
        senior,
        (tenure - 32.0) / 24.0,
        (monthly - 65.0) / 30.0,
        (total - 2300.0) / 2200.0,
        partner,
        dependents,
        paperless,
        phone,
        month,
    ], axis=1)
    raw = {
        "senior_citizen": senior,
        "tenure": tenure,
        "monthly_charges": monthly,
        "total_charges": total,
        "partner": partner,
        "dependents": dependents,
        "paperless": paperless,
        "phone": phone,
        "month_to_month": month,
    }
    return {"x": x, "y": y, "raw": raw, "n": n}


def assign_splits(n: int, rng: np.random.Generator) -> np.ndarray:
    order = rng.permutation(n)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)
    splits = np.empty(n, dtype=object)
    splits[order[:train_end]] = "train"
    splits[order[train_end:val_end]] = "val"
    splits[order[val_end:]] = "test"
    return splits


def make_batch(base: dict, scenario: str, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    n_src = base["n"]
    if scenario == "volume_anomaly":
        take = max(40, int(N_TARGET * 0.12))
    else:
        take = N_TARGET
    idx = rng.choice(n_src, size=take, replace=False)
    x = base["x"][idx].copy()
    y = base["y"][idx].copy()
    raw = {k: base["raw"][k][idx].copy() for k in FEATURE_NAMES}

    if scenario == "feature_drift":
        raw["tenure"] = np.clip(raw["tenure"] * 0.35, 0, None)
        raw["monthly_charges"] = np.clip(raw["monthly_charges"] * 0.55, 0, None)
        x[:, 1] = (raw["tenure"] - 32.0) / 24.0
        x[:, 2] = (raw["monthly_charges"] - 65.0) / 30.0

    if scenario == "label_imbalance":
        target_churn = max(2, int(take * 0.02))
        churn_idx = np.where(y == 1)[0]
        healthy_idx = np.where(y == 0)[0]
        if len(churn_idx) > target_churn:
            keep_churn = rng.choice(churn_idx, size=target_churn, replace=False)
        else:
            keep_churn = churn_idx
        target_healthy = take - len(keep_churn)
        if len(healthy_idx) < target_healthy:
            pad = rng.choice(healthy_idx, size=target_healthy - len(healthy_idx), replace=True)
            keep_healthy = np.concatenate([healthy_idx, pad])
        else:
            keep_healthy = rng.choice(healthy_idx, size=target_healthy, replace=False)
        keep = np.concatenate([keep_healthy, keep_churn])
        rng.shuffle(keep)
        x, y = x[keep], y[keep]
        raw = {k: raw[k][keep] for k in FEATURE_NAMES}

    if scenario == "regression":
        flip = rng.random(len(y)) < 0.40
        y = np.where(flip, 1 - y, y)

    splits = assign_splits(len(y), rng)
    return {"x": x, "y": y, "raw": raw, "splits": splits, "n": len(y)}


def split_xy(batch: dict, split: str):
    mask = batch["splits"] == split
    return batch["x"][mask], batch["y"][mask]


def mean_psi(ref: dict, prod: dict) -> float:
    vals = [psi_numeric(ref["raw"][n], prod["raw"][n]) for n in FEATURE_NAMES]
    return float(np.mean(vals))


def volume_ok(n: int) -> bool:
    ratio = n / N_TARGET
    return (1 - settings.volume_anomaly_tolerance) <= ratio <= (1 + settings.volume_anomaly_tolerance)


def train_lr(batch: dict, seed: int):
    x_tr, y_tr = split_xy(batch, "train")
    x_va, y_va = split_xy(batch, "val")
    x_te, y_te = split_xy(batch, "test")
    model = LogisticRegression(
        max_iter=500,
        class_weight="balanced",
        solver="lbfgs",
        random_state=int(seed) % (2**31),
    )
    model.fit(x_tr, y_tr)
    val_probs = model.predict_proba(x_va)[:, 1]
    threshold = best_threshold_for_f1(val_probs, y_va)
    te_probs = model.predict_proba(x_te)[:, 1]
    te_preds = (te_probs >= threshold).astype(int)
    return classification_metrics(te_probs, te_preds, y_te)


def decide(metrics, champion_metrics):
    gate, reg, reasons = evaluation_gate(metrics, champion_metrics)
    return ("PROMOTED" if gate == "PASS" else "REJECTED"), reg, reasons


def find_csv() -> Path:
    for path in CSV_CANDIDATES:
        if path.is_file():
            return path
    raise FileNotFoundError("ibm-telco-churn.csv not found in /tmp, /app/data, or code/data")


def main() -> None:
    base = load_telco(find_csv())
    rows = []
    for seed in SEEDS:
        log.info("seed %s", seed)
        healthy_ref = None
        champion = None
        first_champion = None
        for i, scenario in enumerate(PLAN):
            gen_name = "healthy" if scenario == "healthy_after_rollback" else scenario
            batch = make_batch(base, gen_name, seed + 17 * (i + 1))
            if healthy_ref is None:
                healthy_ref = batch
            rec = {
                "seed": seed,
                "scenario": scenario,
                "n_rows": batch["n"],
                "psi_mean": round(mean_psi(healthy_ref, batch), 4),
                "drift_level": drift_level(mean_psi(healthy_ref, batch)),
                "outcome": None,
                "f1": None,
                "accuracy": None,
                "regression_pct": None,
                "reasons": None,
            }
            if not volume_ok(batch["n"]):
                rec["outcome"] = "BLOCKED"
                log.info("  %s BLOCKED n=%s", scenario, batch["n"])
                rows.append(rec)
                continue
            metrics = train_lr(batch, seed + 100 * (i + 1))
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
        "corpus": "IBM Telco Customer Churn (public; 7043 rows)",
        "source": "https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d/master/data/Telco-Customer-Churn.csv",
        "family": "sklearn LogisticRegression (L2, class_weight=balanced)",
        "note": "Public labels/features; volume/drift/imbalance/noise scenarios are our perturbations. Exploratory; not used to rescore H1-H3.",
        "features": FEATURE_NAMES,
        "n_seeds": len(SEEDS),
        "n_runs": len(rows),
        "summary": summary,
        "rows": rows,
    }
    OUT.write_text(json.dumps(blob, indent=2) + "\n")
    print(json.dumps({"summary": summary, "n_runs": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
