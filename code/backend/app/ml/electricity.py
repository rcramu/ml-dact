"""Electricity (Elec2) joint-cell helpers.

Loads only the frozen CSV at /app/dat/electricity.csv. No OpenML fetch, no
caller-supplied paths. Folds are 0..4 (five adjacent chronological transfers).
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from .drift import drift_level, psi_numeric
from .evaluation_metrics import classification_metrics
from .gates import evaluation_gate
from .pytorch_trainer import best_threshold_for_f1

CSV_PATH = Path("/app/dat/electricity.csv")
N_BLOCKS = 6
N_FOLDS = N_BLOCKS - 1
MONITOR = ("nswprice", "nswdemand", "vicprice", "vicdemand", "transfer", "period", "day")
FEATURE_COLS = MONITOR
F1_GOOD = 0.70
MODEL_NAME = "electricity-joint"


def _yes_up(value) -> int:
    return 1 if str(value).strip().upper() in {"UP", "1", "TRUE"} else 0


def _to_float(row: dict, name: str) -> float:
    return float(row[name])


@lru_cache(maxsize=1)
def load_rows() -> tuple[dict, ...]:
    if not CSV_PATH.is_file():
        raise FileNotFoundError(f"frozen Electricity CSV missing: {CSV_PATH}")
    with CSV_PATH.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows = sorted(rows, key=lambda r: (_to_float(r, "date"), _to_float(r, "period")))
    return tuple(rows)


def blocks() -> list[list[dict]]:
    rows = list(load_rows())
    n = len(rows)
    block_size = n // N_BLOCKS
    out = [rows[i * block_size:(i + 1) * block_size] for i in range(N_BLOCKS)]
    leftover = rows[N_BLOCKS * block_size:]
    if leftover:
        out[-1] = out[-1] + leftover
    return out


def encode_xy(rows: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    x = np.array([[_to_float(r, c) for c in FEATURE_COLS] for r in rows], dtype=float)
    y = np.array([_yes_up(r["target"]) for r in rows], dtype=int)
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


def mean_psi(ref_rows: list[dict], prod_rows: list[dict]) -> float:
    vals = []
    for name in MONITOR:
        ref = np.array([_to_float(r, name) for r in ref_rows], dtype=float)
        prod = np.array([_to_float(r, name) for r in prod_rows], dtype=float)
        vals.append(psi_numeric(ref, prod))
    return float(np.mean(vals)) if vals else 0.0


def per_feature_psi(ref_rows: list[dict], prod_rows: list[dict]) -> dict:
    out = {}
    for name in MONITOR:
        ref = np.array([_to_float(r, name) for r in ref_rows], dtype=float)
        prod = np.array([_to_float(r, name) for r in prod_rows], dtype=float)
        out[name] = round(float(psi_numeric(ref, prod)), 4)
    return out


def train_hgb(rows: list[dict], seed: int):
    rng = np.random.default_rng(seed)
    x, y = encode_xy(rows)
    splits = assign_splits(len(rows), rng)
    tr, va, te = splits == "train", splits == "val", splits == "test"
    model = HistGradientBoostingClassifier(
        max_depth=6,
        learning_rate=0.10,
        max_iter=120,
        random_state=int(seed) % (2**31),
    )
    model.fit(x[tr], y[tr])
    threshold = best_threshold_for_f1(model.predict_proba(x[va])[:, 1], y[va])
    te_probs = model.predict_proba(x[te])[:, 1]
    te_preds = (te_probs >= threshold).astype(int)
    metrics = classification_metrics(te_probs, te_preds, y[te])
    return model, threshold, metrics


def score_model(model, threshold, rows: list[dict], seed: int) -> dict:
    rng = np.random.default_rng(seed)
    x, y = encode_xy(rows)
    splits = assign_splits(len(rows), rng)
    te = splits == "test"
    if int(te.sum()) < 5:
        return {"f1": None, "precision": None, "recall": None, "level": "UNKNOWN", "n_test": int(te.sum())}
    probs = model.predict_proba(x[te])[:, 1]
    preds = (probs >= threshold).astype(int)
    metrics = classification_metrics(probs, preds, y[te])
    metrics["level"] = "GOOD" if metrics["f1"] >= F1_GOOD else "BAD"
    metrics["n_test"] = int(te.sum())
    return metrics


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


def score_fold(fold: int, train_candidate: bool = False) -> dict:
    if fold not in range(N_FOLDS):
        raise ValueError("fold must be 0, 1, 2, 3, or 4")
    parts = blocks()
    ref, prod = parts[fold], parts[fold + 1]
    champ_model, champ_thr, champ_metrics = train_hgb(ref, seed=9700 + fold)
    champ_outcome, _, champ_reasons = evaluation_gate(champ_metrics, None)
    psi = mean_psi(ref, prod)
    dlev = drift_level(psi)
    ev = score_model(champ_model, champ_thr, prod, seed=9800 + fold)
    elev = ev["level"]
    fire = dlev == "SIGNIFICANT" and elev != "GOOD"
    rec = {
        "model": MODEL_NAME,
        "fold": fold,
        "n_ref": len(ref),
        "n_prod": len(prod),
        "ref_date_min": float(min(_to_float(r, "date") for r in ref)),
        "ref_date_max": float(max(_to_float(r, "date") for r in ref)),
        "prod_date_min": float(min(_to_float(r, "date") for r in prod)),
        "prod_date_max": float(max(_to_float(r, "date") for r in prod)),
        "psi_mean": round(psi, 4),
        "psi_per_feature": per_feature_psi(ref, prod),
        "drift_level": dlev,
        "champion_f1_ref": round(champ_metrics["f1"], 4),
        "champion_precision_ref": round(champ_metrics["precision"], 4),
        "champion_recall_ref": round(champ_metrics["recall"], 4),
        "champion_first_version": "PROMOTED" if champ_outcome == "PASS" else "REJECTED",
        "champion_first_reasons": champ_reasons,
        "champion_f1_prod": None if ev.get("f1") is None else round(ev["f1"], 4),
        "champion_precision_prod": None if ev.get("precision") is None else round(ev["precision"], 4),
        "champion_recall_prod": None if ev.get("recall") is None else round(ev["recall"], 4),
        "evaluation_level": elev,
        "matrix_cell": cell(dlev, elev),
        "joint_retrain": fire,
        "predicate": "Retrain = (DriftLevel == SIGNIFICANT) and (EvaluationLevel != GOOD)",
        "candidate_trained": False,
        "candidate_f1_prod": None,
        "candidate_precision_prod": None,
        "candidate_recall_prod": None,
        "delta_f1_on_prod": None,
        "gate": None,
        "regression_pct": None,
        "gate_reasons": None,
    }
    if train_candidate:
        _cand_model, _cand_thr, cand_metrics = train_hgb(prod, seed=9900 + fold)
        gate, reg, reasons = evaluation_gate(
            cand_metrics,
            champ_metrics if champ_outcome == "PASS" else None,
        )
        rec["candidate_trained"] = True
        rec["candidate_f1_prod"] = round(cand_metrics["f1"], 4)
        rec["candidate_precision_prod"] = round(cand_metrics["precision"], 4)
        rec["candidate_recall_prod"] = round(cand_metrics["recall"], 4)
        rec["delta_f1_on_prod"] = None if ev.get("f1") is None else round(cand_metrics["f1"] - ev["f1"], 4)
        rec["gate"] = "PROMOTED" if gate == "PASS" else "REJECTED"
        rec["regression_pct"] = reg
        rec["gate_reasons"] = reasons
        rec["champion_metrics"] = {
            "f1": champ_metrics["f1"],
            "precision": champ_metrics["precision"],
            "recall": champ_metrics["recall"],
            "accuracy": champ_metrics.get("accuracy", 0.0),
            "roc_auc": champ_metrics.get("roc_auc", 0.0),
            "pr_auc": champ_metrics.get("pr_auc", 0.0),
        }
        rec["candidate_metrics"] = cand_metrics
    return rec
