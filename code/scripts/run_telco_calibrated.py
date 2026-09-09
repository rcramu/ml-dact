"""Exploratory Telco transfer with full one-hot schema and a calibrated floor.

Table 13: 9 features, LR, published Algorithm 1 (F1>=0.70) rejected every
trained candidate. This run trains HistGradientBoosting on the full public
schema and scores TWO gates on the same draws:

  published  — F1>=0.70, P/R>=0.60, 10% budget, recall-vs-champion
  calibrated — F1>=0.55, P/R>=0.50, 10% budget, recall-vs-champion

The calibrated cell is pre-specified from Table 13's mean healthy F1 (0.600),
not tuned after seeing these seeds. DriftLevel uses the same 9 monitor
features as Table 13 so mean-PSI is not diluted by one-hot columns.
Scenario shifts remain ours. In-process; does not rescore H1-H3.
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
from app.ml.pytorch_trainer import best_threshold_for_f1

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("telco-calibrated")

CSV_CANDIDATES = [
    Path("/tmp/ibm-telco-churn.csv"),
    Path("/app/dat/ibm-telco-churn.csv"),
]
SEEDS = [9501, 9502, 9503, 9504, 9505]
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
NUM_COLS = ["SeniorCitizen", "tenure", "MonthlyCharges", "TotalCharges"]
N_TARGET = 1500
GATES = {
    "published": {"f1": 0.70, "precision": 0.60, "recall": 0.60, "max_reg": 10.0},
    "calibrated": {"f1": 0.55, "precision": 0.50, "recall": 0.50, "max_reg": 10.0},
}
OUT = Path("/tmp/telco-calibrated.json")


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


def make_batch(base: list[dict], scenario: str, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    n_src = len(base)
    take = max(40, int(N_TARGET * 0.12)) if scenario == "volume_anomaly" else N_TARGET
    idx = rng.choice(n_src, size=take, replace=False)
    rows = [dict(base[i]) for i in idx]
    if scenario == "feature_drift":
        for row in rows:
            row["tenure"] = str(max(0.0, float(row["tenure"]) * 0.35))
            row["MonthlyCharges"] = str(max(0.0, float(row["MonthlyCharges"]) * 0.55))
    if scenario == "label_imbalance":
        y = np.array([_yes(r["Churn"]) for r in rows], dtype=int)
        target_churn = max(2, int(take * 0.02))
        churn_idx = np.where(y == 1)[0]
        healthy_idx = np.where(y == 0)[0]
        keep_churn = rng.choice(churn_idx, size=min(target_churn, len(churn_idx)), replace=False)
        target_healthy = take - len(keep_churn)
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


def volume_ok(n: int) -> bool:
    ratio = n / N_TARGET
    return 0.80 <= ratio <= 1.20


def gate(candidate: dict, champion: dict | None, spec: dict) -> tuple[str, float | None, str]:
    reasons = []
    if candidate["f1"] < spec["f1"]:
        reasons.append(f"F1 {candidate['f1']:.3f} < {spec['f1']:.2f}")
    if candidate["recall"] < spec["recall"]:
        reasons.append(f"recall {candidate['recall']:.3f} < {spec['recall']:.2f}")
    if candidate["precision"] < spec["precision"]:
        reasons.append(f"precision {candidate['precision']:.3f} < {spec['precision']:.2f}")
    regression_pct = None
    if champion is not None and champion.get("f1", 0) > 0:
        regression_pct = round(((champion["f1"] - candidate["f1"]) / champion["f1"]) * 100, 2)
        if regression_pct > spec["max_reg"]:
            reasons.append(f"F1 regression {regression_pct:.2f}% > {spec['max_reg']:.1f}%")
        if candidate["recall"] < champion.get("recall", 0):
            reasons.append(
                f"recall {candidate['recall']:.3f} < champion {champion['recall']:.3f}"
            )
    result = "FAIL" if reasons else "PASS"
    return ("PROMOTED" if result == "PASS" else "REJECTED"), regression_pct, "; ".join(reasons) or "pass"


def train_hgb(batch: dict, encoder: OneHotEncoder, seed: int) -> dict:
    x, y = encode_xy(batch["rows"], encoder)
    tr, va, te = batch["splits"] == "train", batch["splits"] == "val", batch["splits"] == "test"
    model = HistGradientBoostingClassifier(
        max_depth=6,
        learning_rate=0.10,
        max_iter=120,
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
    encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    encoder.fit(np.array([[r[c] for c in CAT_COLS] for r in base], dtype=object))
    rows = []
    for seed in SEEDS:
        log.info("seed %s", seed)
        healthy_ref = None
        champions = {"published": None, "calibrated": None}
        first_champions = {"published": None, "calibrated": None}
        for i, scenario in enumerate(PLAN):
            gen_name = "healthy" if scenario == "healthy_after_rollback" else scenario
            if scenario == "healthy_after_rollback":
                champions = dict(first_champions)
            batch = make_batch(base, gen_name, seed + 17 * (i + 1))
            if healthy_ref is None:
                healthy_ref = batch["rows"]
            rec = {
                "seed": seed,
                "scenario": scenario,
                "n_rows": batch["n"],
                "psi_mean": round(mean_psi(healthy_ref, batch["rows"]), 4),
                "drift_level": drift_level(mean_psi(healthy_ref, batch["rows"])),
                "f1": None,
                "accuracy": None,
                "precision": None,
                "recall": None,
                "published": None,
                "calibrated": None,
            }
            if not volume_ok(batch["n"]):
                rec["published"] = {"outcome": "BLOCKED"}
                rec["calibrated"] = {"outcome": "BLOCKED"}
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
            for name, spec in GATES.items():
                outcome, reg, reasons = gate(metrics, champions[name], spec)
                rec[name] = {"outcome": outcome, "regression_pct": reg, "reasons": reasons}
                if outcome == "PROMOTED":
                    champions[name] = metrics
                    if first_champions[name] is None:
                        first_champions[name] = metrics
            log.info(
                "  %s F1=%s PSI=%s pub=%s cal=%s",
                scenario, rec["f1"], rec["psi_mean"],
                rec["published"]["outcome"], rec["calibrated"]["outcome"],
            )
            rows.append(rec)

    def summarize(arm: str) -> dict:
        out = {}
        for scenario in PLAN:
            items = [r for r in rows if r["scenario"] == scenario]
            f1s = [r["f1"] for r in items if r["f1"] is not None]
            out[scenario] = {
                "outcomes": {
                    k: sum(1 for r in items if r[arm]["outcome"] == k)
                    for k in ("PROMOTED", "REJECTED", "BLOCKED")
                },
                "mean_f1": round(float(np.mean(f1s)), 4) if f1s else None,
                "mean_psi": round(float(np.mean([r["psi_mean"] for r in items])), 4),
            }
        return out

    blob = {
        "corpus": "IBM Telco Customer Churn (public; 7043 rows; full one-hot schema)",
        "family": "sklearn HistGradientBoostingClassifier",
        "monitor": "Table 13's 9 features (mean PSI not taken over one-hot columns)",
        "gates": GATES,
        "note": (
            "Calibrated floors pre-specified from Table 13 mean healthy F1 0.600. "
            "Perturbations are ours. Exploratory; not used to rescore H1-H3."
        ),
        "n_seeds": len(SEEDS),
        "n_runs": len(rows),
        "n_features": int(4 + encoder.transform(np.array([[base[0][c] for c in CAT_COLS]], dtype=object)).shape[1]),
        "summary": {name: summarize(name) for name in GATES},
        "rows": rows,
    }
    OUT.write_text(json.dumps(blob, indent=2) + "\n")
    print(json.dumps({"n_features": blob["n_features"], "summary": blob["summary"]}, indent=2))


if __name__ == "__main__":
    main()
