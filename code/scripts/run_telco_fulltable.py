"""Exploratory Telco replay: full public table + class-balanced HGB.

Tables 13 and 15 used 1,500-row draws. Healthy F1 stayed below F1_min=0.70
(mean 0.600 LR; 0.547 HGB). This run is pre-specified before seeing these
seeds:

  - use every public row (7,043), not a 1,500-row subsample
  - HistGradientBoosting with class_weight='balanced', max_iter=200
  - published Algorithm 1 only (F1>=0.70, P/R>=0.60, 10%, recall-vs-champion)
  - same nine monitor features as Table 13
  - scenario shifts remain ours

In-process. Not used to rescore H1-H3.
"""
import csv
import json
import logging
import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import OneHotEncoder

sys.path.insert(0, str(Path("/app")))

from app.ml.drift import drift_level, psi_numeric
from app.ml.evaluation_metrics import classification_metrics
from app.ml.gates import evaluation_gate
from app.ml.pytorch_trainer import best_threshold_for_f1

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("telco-fulltable")

CSV_CANDIDATES = [
    Path("/tmp/ibm-telco-churn.csv"),
    Path("/app/data/ibm-telco-churn.csv"),
    Path(__file__).resolve().parents[1] / "data" / "ibm-telco-churn.csv",
]
SEEDS = [9901, 9902, 9903, 9904, 9905]
PLAN = [
    "healthy",
    "volume_anomaly",
    "feature_drift",
    "label_imbalance",
    "regression",
    "healthy_after_rollback",
]
MONITOR = [
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
CAT_COLS = [
    "gender", "Partner", "Dependents", "PhoneService", "MultipleLines",
    "InternetService", "OnlineSecurity", "OnlineBackup", "DeviceProtection",
    "TechSupport", "StreamingTV", "StreamingMovies", "Contract",
    "PaperlessBilling", "PaymentMethod",
]
OUT_CANDIDATES = [
    Path("/tmp/metrics/telco-fulltable.json"),
    Path("/tmp/telco-fulltable.json"),
]


def _yes(value: str) -> float:
    return 1.0 if str(value).strip().lower() == "yes" else 0.0


def _float(value: str) -> float:
    text = str(value).strip()
    return float(text) if text else 0.0


def find_csv() -> Path:
    for path in CSV_CANDIDATES:
        if path.is_file():
            return path
    raise FileNotFoundError("ibm-telco-churn.csv not found")


def load_raw(path: Path) -> list[dict]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def monitor_of(rows: list[dict]) -> dict:
    return {
        "senior_citizen": np.array([float(r["SeniorCitizen"]) for r in rows], dtype=float),
        "tenure": np.array([float(r["tenure"]) for r in rows], dtype=float),
        "monthly_charges": np.array([float(r["MonthlyCharges"]) for r in rows], dtype=float),
        "total_charges": np.array([_float(r["TotalCharges"]) for r in rows], dtype=float),
        "partner": np.array([_yes(r["Partner"]) for r in rows], dtype=float),
        "dependents": np.array([_yes(r["Dependents"]) for r in rows], dtype=float),
        "paperless": np.array([_yes(r["PaperlessBilling"]) for r in rows], dtype=float),
        "phone": np.array([_yes(r["PhoneService"]) for r in rows], dtype=float),
        "month_to_month": np.array(
            [1.0 if r["Contract"].strip() == "Month-to-month" else 0.0 for r in rows],
            dtype=float,
        ),
    }


def mean_psi(ref_rows: list[dict], prod_rows: list[dict]) -> float:
    ref = monitor_of(ref_rows)
    prod = monitor_of(prod_rows)
    return float(np.mean([psi_numeric(ref[n], prod[n]) for n in MONITOR]))


def encode_xy(rows: list[dict], encoder: OneHotEncoder) -> tuple[np.ndarray, np.ndarray]:
    cats = np.array([[r[c] for c in CAT_COLS] for r in rows], dtype=object)
    nums = np.array([
        [float(r["SeniorCitizen"]), float(r["tenure"]), float(r["MonthlyCharges"]), _float(r["TotalCharges"])]
        for r in rows
    ], dtype=float)
    nums[:, 1] = (nums[:, 1] - 32.0) / 24.0
    nums[:, 2] = (nums[:, 2] - 65.0) / 30.0
    nums[:, 3] = (nums[:, 3] - 2300.0) / 2200.0
    x = np.hstack([nums, encoder.transform(cats)])
    y = np.array([_yes(r["Churn"]) for r in rows], dtype=int)
    return x, y


def assign_splits(n: int, rng: np.random.Generator) -> np.ndarray:
    order = rng.permutation(n)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)
    splits = np.empty(n, dtype=object)
    splits[order[:train_end]] = "train"
    splits[order[train_end:val_end]] = "val"
    splits[order[val_end:]] = "test"
    return splits


def make_batch(base: list[dict], scenario: str, seed: int, n_target: int) -> dict:
    rng = np.random.default_rng(seed)
    rows = [dict(r) for r in base]
    if scenario == "volume_anomaly":
        take = max(40, int(n_target * 0.12))
        idx = rng.choice(len(rows), size=take, replace=False)
        rows = [rows[i] for i in idx]
    if scenario == "feature_drift":
        for row in rows:
            row["tenure"] = str(max(0.0, float(row["tenure"]) * 0.35))
            row["MonthlyCharges"] = str(max(0.0, float(row["MonthlyCharges"]) * 0.55))
    if scenario == "label_imbalance":
        y = np.array([_yes(r["Churn"]) for r in rows], dtype=int)
        target_churn = max(2, int(len(rows) * 0.02))
        churn_idx = np.where(y == 1)[0]
        healthy_idx = np.where(y == 0)[0]
        keep_churn = rng.choice(churn_idx, size=min(target_churn, len(churn_idx)), replace=False)
        target_healthy = len(rows) - len(keep_churn)
        if len(healthy_idx) < target_healthy:
            pad = rng.choice(healthy_idx, size=target_healthy - len(healthy_idx), replace=True)
            keep_healthy = np.concatenate([healthy_idx, pad])
        else:
            keep_healthy = rng.choice(healthy_idx, size=target_healthy, replace=False)
        keep = np.concatenate([keep_healthy, keep_churn])
        rng.shuffle(keep)
        rows = [rows[i] for i in keep]
    if scenario == "regression":
        for row in rows:
            if rng.random() < 0.40:
                row["Churn"] = "No" if row["Churn"] == "Yes" else "Yes"
    return {"rows": rows, "splits": assign_splits(len(rows), rng), "n": len(rows)}


def volume_ok(n: int, n_target: int) -> bool:
    ratio = n / n_target
    return 0.80 <= ratio <= 1.20


def train_hgb(batch: dict, encoder: OneHotEncoder, seed: int) -> dict:
    x, y = encode_xy(batch["rows"], encoder)
    tr, va, te = batch["splits"] == "train", batch["splits"] == "val", batch["splits"] == "test"
    model = HistGradientBoostingClassifier(
        max_depth=6,
        learning_rate=0.10,
        max_iter=200,
        class_weight="balanced",
        random_state=int(seed) % (2**31),
    )
    model.fit(x[tr], y[tr])
    val_probs = model.predict_proba(x[va])[:, 1]
    threshold = best_threshold_for_f1(val_probs, y[va])
    te_probs = model.predict_proba(x[te])[:, 1]
    te_preds = (te_probs >= threshold).astype(int)
    return classification_metrics(te_probs, te_preds, y[te])


def main() -> None:
    base = load_raw(find_csv())
    n_target = len(base)
    encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    encoder.fit(np.array([[r[c] for c in CAT_COLS] for r in base], dtype=object))
    rows = []
    for seed in SEEDS:
        log.info("seed %s", seed)
        healthy_ref = None
        champion = None
        first_champion = None
        for i, scenario in enumerate(PLAN):
            gen_name = "healthy" if scenario == "healthy_after_rollback" else scenario
            if scenario == "healthy_after_rollback":
                champion = first_champion
            batch = make_batch(base, gen_name, seed + 17 * (i + 1), n_target)
            if healthy_ref is None:
                healthy_ref = batch["rows"]
            psi = mean_psi(healthy_ref, batch["rows"])
            rec = {
                "seed": seed,
                "scenario": scenario,
                "n_rows": batch["n"],
                "psi_mean": round(psi, 4),
                "drift_level": drift_level(psi),
                "f1": None,
                "accuracy": None,
                "precision": None,
                "recall": None,
                "outcome": None,
                "regression_pct": None,
                "reasons": None,
            }
            if not volume_ok(batch["n"], n_target):
                rec["outcome"] = "BLOCKED"
                log.info("  %s BLOCKED n=%s PSI=%s", scenario, batch["n"], rec["psi_mean"])
                rows.append(rec)
                continue
            metrics = train_hgb(batch, encoder, seed + 100 * (i + 1))
            rec.update({
                "f1": round(metrics["f1"], 4),
                "accuracy": round(metrics["accuracy"], 4),
                "precision": round(metrics["precision"], 4),
                "recall": round(metrics["recall"], 4),
            })
            result, reg, reasons = evaluation_gate(metrics, champion)
            rec["outcome"] = "PROMOTED" if result == "PASS" else "REJECTED"
            rec["regression_pct"] = reg
            rec["reasons"] = reasons
            if result == "PASS":
                champion = metrics
                if first_champion is None:
                    first_champion = metrics
            log.info(
                "  %s F1=%s P=%s R=%s PSI=%s %s %s",
                scenario, rec["f1"], rec["precision"], rec["recall"],
                rec["psi_mean"], rec["drift_level"], rec["outcome"],
            )
            rows.append(rec)

    summary = {}
    for scenario in PLAN:
        items = [r for r in rows if r["scenario"] == scenario]
        f1s = [r["f1"] for r in items if r["f1"] is not None]
        summary[scenario] = {
            "outcomes": {
                k: sum(1 for r in items if r["outcome"] == k)
                for k in ("PROMOTED", "REJECTED", "BLOCKED")
            },
            "mean_f1": round(float(np.mean(f1s)), 4) if f1s else None,
            "mean_precision": round(float(np.mean([r["precision"] for r in items if r["precision"] is not None])), 4) if f1s else None,
            "mean_recall": round(float(np.mean([r["recall"] for r in items if r["recall"] is not None])), 4) if f1s else None,
            "mean_psi": round(float(np.mean([r["psi_mean"] for r in items])), 4),
        }
    healthy = [r for r in rows if r["scenario"] == "healthy" and r["f1"] is not None]
    drift = [r for r in rows if r["scenario"] == "feature_drift" and r["f1"] is not None]
    paired = []
    for seed in SEEDS:
        h = next(r for r in rows if r["seed"] == seed and r["scenario"] == "healthy")
        d = next(r for r in rows if r["seed"] == seed and r["scenario"] == "feature_drift")
        if h["outcome"] == "PROMOTED" and d["f1"] is not None:
            paired.append(round(d["f1"] - h["f1"], 4))
    blob = {
        "corpus": "IBM Telco Customer Churn (public; 7043 rows; full table; full one-hot schema)",
        "family": "sklearn HistGradientBoostingClassifier class_weight=balanced max_iter=200",
        "monitor": "Table 13's 9 features (mean PSI not taken over one-hot columns)",
        "gate": "published Algorithm 1 (F1>=0.70, P/R>=0.60, 10%, recall-vs-champion)",
        "note": (
            "Full public table, not a 1,500-row draw. class_weight and max_iter "
            "pre-specified before these seeds. Perturbations are ours. "
            "Exploratory; not used to rescore H1-H3."
        ),
        "n_seeds": len(SEEDS),
        "n_runs": len(rows),
        "n_rows_healthy": n_target,
        "n_features": int(4 + encoder.transform(np.array([[base[0][c] for c in CAT_COLS]], dtype=object)).shape[1]),
        "healthy_promoted": sum(1 for r in healthy if r["outcome"] == "PROMOTED"),
        "paired_h2_deltas": paired,
        "n_paired_h2": len(paired),
        "summary": summary,
        "rows": rows,
    }
    out = next((p for p in OUT_CANDIDATES if p.parent.is_dir()), OUT_CANDIDATES[-1])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(blob, indent=2) + "\n")
    log.info("wrote %s", out)
    print(json.dumps({k: blob[k] for k in blob if k != "rows"}, indent=2))
    for r in rows:
        print(
            f"seed {r['seed']} {r['scenario']:24} n={r['n_rows']:4} "
            f"F1={r['f1']} {r['drift_level']:12} {r['outcome']}"
        )


if __name__ == "__main__":
    main()
