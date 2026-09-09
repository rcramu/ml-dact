"""Exploratory natural-drift transfer on the public Electricity (Elec2) corpus.

Unlike Tables 13 and 15, this run does not inject feature, label, or volume
shifts. Rows stay in the published chronological order. date is used only to
order windows; it is excluded from the model and from mean PSI so DriftLevel
is not SIGNIFICANT by construction of the split.

Protocol (pre-specified):
  - 6 equal chronological blocks
  - 5 adjacent transfers: block i (reference / champion) -> block i+1 (production)
  - HistGradientBoosting, published Algorithm 1 (F1>=0.70, P/R>=0.60, 10%)
  - EvaluationLevel GOOD iff champion F1 on the production test split >= 0.70
  - Joint cell: Retrain = (DriftLevel == SIGNIFICANT) and (EvaluationLevel != GOOD)
  - A candidate is always trained on the production block so a paired F1
    comparison can be scored even when the joint cell does not fire

In-process. Not a live Airflow trigger. Not used to rescore H1-H3.
"""
import csv
import json
import logging
import sys
from pathlib import Path

import numpy as np
from sklearn.datasets import fetch_openml
from sklearn.ensemble import HistGradientBoostingClassifier

sys.path.insert(0, str(Path("/app")))

from app.ml.drift import drift_level, psi_numeric
from app.ml.evaluation_metrics import classification_metrics
from app.ml.gates import evaluation_gate
from app.ml.pytorch_trainer import best_threshold_for_f1

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("electricity-natural")

OPENML_ID = 151
N_BLOCKS = 6
MONITOR = ("nswprice", "nswdemand", "vicprice", "vicdemand", "transfer", "period", "day")
FEATURE_COLS = MONITOR  # date excluded
F1_GOOD = 0.70
CSV_CANDIDATES = [
    Path("/tmp/data/electricity.csv"),
    Path("/app/data/electricity.csv"),
    Path(__file__).resolve().parents[1] / "data" / "electricity.csv",
]
OUT_CANDIDATES = [
    Path("/tmp/metrics/electricity-natural.json"),
    Path("/tmp/electricity-natural.json"),
]
CSV_OUT = Path("/tmp/data/electricity.csv")


def _yes_up(value) -> int:
    return 1 if str(value).strip().upper() in {"UP", "1", "TRUE"} else 0


def load_or_fetch() -> list[dict]:
    for path in CSV_CANDIDATES:
        if path.is_file():
            log.info("loading %s", path)
            with path.open(newline="") as handle:
                return list(csv.DictReader(handle))
    log.info("fetching OpenML electricity id=%s", OPENML_ID)
    frame = fetch_openml(data_id=OPENML_ID, as_frame=True, parser="auto")
    data = frame.frame.copy()
    data.columns = [c.lower() for c in data.columns]
    rename = {"class": "target"}
    data = data.rename(columns=rename)
    if "target" not in data.columns:
        data["target"] = frame.target
    rows = data.to_dict(orient="records")
    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["date", "day", "period", "nswprice", "nswdemand", "vicprice", "vicdemand", "transfer", "target"]
    with CSV_OUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] for k in fieldnames})
    log.info("wrote %s rows=%s", CSV_OUT, len(rows))
    return rows


def to_float(row: dict, name: str) -> float:
    return float(row[name])


def encode_xy(rows: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    x = np.array([[to_float(r, c) for c in FEATURE_COLS] for r in rows], dtype=float)
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
        ref = np.array([to_float(r, name) for r in ref_rows], dtype=float)
        prod = np.array([to_float(r, name) for r in prod_rows], dtype=float)
        vals.append(psi_numeric(ref, prod))
    return float(np.mean(vals)) if vals else 0.0


def per_feature_psi(ref_rows: list[dict], prod_rows: list[dict]) -> dict:
    out = {}
    for name in MONITOR:
        ref = np.array([to_float(r, name) for r in ref_rows], dtype=float)
        prod = np.array([to_float(r, name) for r in prod_rows], dtype=float)
        out[name] = round(float(psi_numeric(ref, prod)), 4)
    return out


def train_hgb(rows: list[dict], seed: int) -> tuple[object, float, dict, np.ndarray]:
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
    return model, threshold, metrics, splits


def score_model(model, threshold, rows: list[dict], seed: int) -> dict:
    rng = np.random.default_rng(seed)
    x, y = encode_xy(rows)
    splits = assign_splits(len(rows), rng)
    te = splits == "test"
    if int(te.sum()) < 5:
        return {"f1": None, "level": "UNKNOWN", "n_test": int(te.sum())}
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


def main() -> None:
    rows = load_or_fetch()
    rows = sorted(rows, key=lambda r: (to_float(r, "date"), to_float(r, "period")))
    n = len(rows)
    block_size = n // N_BLOCKS
    blocks = [rows[i * block_size:(i + 1) * block_size] for i in range(N_BLOCKS)]
    leftover = rows[N_BLOCKS * block_size:]
    if leftover:
        blocks[-1] = blocks[-1] + leftover

    transfers = []
    for fold in range(N_BLOCKS - 1):
        ref, prod = blocks[fold], blocks[fold + 1]
        log.info("fold %s ref=%s prod=%s", fold, len(ref), len(prod))
        champ_model, champ_thr, champ_metrics, _ = train_hgb(ref, seed=9700 + fold)
        champ_outcome, _, champ_reasons = evaluation_gate(champ_metrics, None)
        psi = mean_psi(ref, prod)
        dlev = drift_level(psi)
        ev = score_model(champ_model, champ_thr, prod, seed=9800 + fold)
        elev = ev["level"]
        fire = dlev == "SIGNIFICANT" and elev != "GOOD"
        cand_model, cand_thr, cand_metrics, _ = train_hgb(prod, seed=9900 + fold)
        gate, reg, reasons = evaluation_gate(
            cand_metrics,
            champ_metrics if champ_outcome == "PASS" else None,
        )
        rec = {
            "fold": fold,
            "n_ref": len(ref),
            "n_prod": len(prod),
            "ref_date_min": float(min(to_float(r, "date") for r in ref)),
            "ref_date_max": float(max(to_float(r, "date") for r in ref)),
            "prod_date_min": float(min(to_float(r, "date") for r in prod)),
            "prod_date_max": float(max(to_float(r, "date") for r in prod)),
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
            "candidate_f1_prod": round(cand_metrics["f1"], 4),
            "candidate_precision_prod": round(cand_metrics["precision"], 4),
            "candidate_recall_prod": round(cand_metrics["recall"], 4),
            "delta_f1_on_prod": None if ev.get("f1") is None else round(cand_metrics["f1"] - ev["f1"], 4),
            "gate": "PROMOTED" if gate == "PASS" else "REJECTED",
            "regression_pct": reg,
            "gate_reasons": reasons,
        }
        log.info(
            "  PSI=%s %s champ_ref=%s champ_prod=%s %s cand=%s gate=%s fire=%s",
            rec["psi_mean"], dlev, rec["champion_f1_ref"], rec["champion_f1_prod"],
            elev, rec["candidate_f1_prod"], rec["gate"], fire,
        )
        transfers.append(rec)

    fires = sum(1 for r in transfers if r["joint_retrain"])
    sig_bad = sum(1 for r in transfers if r["drift_level"] == "SIGNIFICANT" and r["evaluation_level"] == "BAD")
    lifts = [r["delta_f1_on_prod"] for r in transfers if r["delta_f1_on_prod"] is not None]
    blob = {
        "corpus": "Electricity (Elec2), OpenML 151; public; chronological order preserved",
        "family": "sklearn HistGradientBoostingClassifier",
        "monitor": list(MONITOR),
        "note": (
            "No injected shifts. date excluded from the model and from mean PSI. "
            "Five adjacent chronological transfers. Exploratory; not used to rescore H1-H3. "
            "Not a live Airflow trigger."
        ),
        "n_rows": n,
        "n_blocks": N_BLOCKS,
        "n_transfers": len(transfers),
        "joint_fires": fires,
        "significant_x_bad": sig_bad,
        "mean_psi": round(float(np.mean([r["psi_mean"] for r in transfers])), 4),
        "mean_champion_f1_ref": round(float(np.mean([r["champion_f1_ref"] for r in transfers])), 4),
        "mean_champion_f1_prod": round(float(np.mean([r["champion_f1_prod"] for r in transfers if r["champion_f1_prod"] is not None])), 4),
        "mean_candidate_f1_prod": round(float(np.mean([r["candidate_f1_prod"] for r in transfers])), 4),
        "mean_delta_f1_on_prod": round(float(np.mean(lifts)), 4) if lifts else None,
        "promoted": sum(1 for r in transfers if r["gate"] == "PROMOTED"),
        "rejected": sum(1 for r in transfers if r["gate"] == "REJECTED"),
        "transfers": transfers,
    }
    out = next((p for p in OUT_CANDIDATES if p.parent.is_dir()), OUT_CANDIDATES[-1])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(blob, indent=2) + "\n")
    log.info("wrote %s", out)
    print(json.dumps({k: blob[k] for k in blob if k != "transfers"}, indent=2))
    for r in transfers:
        print(
            f"fold {r['fold']} PSI={r['psi_mean']:.3f} {r['drift_level']:12} "
            f"champ {r['champion_f1_ref']:.3f}->{r['champion_f1_prod']} {r['evaluation_level']:8} "
            f"cand={r['candidate_f1_prod']:.3f} dF1={r['delta_f1_on_prod']} "
            f"{r['gate']:9} {'FIRE' if r['joint_retrain'] else 'hold':4} {r['matrix_cell']}"
        )


if __name__ == "__main__":
    main()
