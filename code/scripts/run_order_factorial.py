"""Exploratory 4! factorial of the four stress scenarios (MLP, Algorithm 1).

Healthy opener and rollback coda are fixed. Rollback happens after all four
stress runs, matching Table 7, not mid-sequence. In-process; does not touch
confirmatory registry names. n=1 seed per permutation.
"""
import json
import logging
import sys
from itertools import permutations
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
log = logging.getLogger("order-factorial")

STRESS = (
    "volume_anomaly",
    "feature_drift",
    "label_imbalance",
    "regression",
)
OUT = Path("/tmp/order-factorial.json")


def arrays(records, split):
    return gen.records_to_arrays(records, split)


def mean_psi(ref_records, prod_records) -> float:
    ref = {n: np.array([r[n] for r in ref_records], dtype=float) for n in gen.FEATURE_NAMES}
    prod = {n: np.array([r[n] for r in prod_records], dtype=float) for n in gen.FEATURE_NAMES}
    return float(np.mean([psi_numeric(ref[n], prod[n]) for n in gen.FEATURE_NAMES]))


def volume_ok(n: int) -> bool:
    ratio = n / settings.expected_volume
    return (1 - settings.volume_anomaly_tolerance) <= ratio <= (1 + settings.volume_anomaly_tolerance)


def train_mlp(records, seed: int):
    x_tr, y_tr = arrays(records, "train")
    x_va, y_va = arrays(records, "val")
    x_te, y_te = arrays(records, "test")
    trained, _loss = train_model(
        x_tr, y_tr,
        epochs=settings.train_epochs,
        batch_size=settings.train_batch_size,
        learning_rate=settings.train_learning_rate,
        hidden1=settings.hidden_dim_1,
        hidden2=settings.hidden_dim_2,
        seed=int(seed) % (2**31),
    )
    val_probs = predict(trained, x_va) if len(y_va) else np.array([])
    threshold = best_threshold_for_f1(val_probs, y_va) if len(y_va) else 0.5
    te_probs = predict(trained, x_te) if len(y_te) else np.array([])
    te_preds = (te_probs >= threshold).astype(int) if len(y_te) else np.array([])
    metrics = classification_metrics(te_probs, te_preds, y_te) if len(y_te) else {}
    return metrics


def decide(metrics, champion_metrics):
    gate, reg, reasons = evaluation_gate(metrics, champion_metrics)
    return ("PROMOTED" if gate == "PASS" else "REJECTED"), reg, reasons


def champion_context(drift_promoted: bool, champion, first_champion) -> str:
    if drift_promoted:
        return "post_drift"
    if champion is None or champion is first_champion:
        return "first_healthy"
    return "other"


def run_one(perm_id: int, order: tuple[str, ...]) -> list[dict]:
    seed = 9401 + perm_id
    log.info("perm %s order=%s", perm_id, ",".join(order))
    rows = []
    healthy_ref = None
    champion = None
    first_champion = None
    drift_promoted = False
    plan = ["healthy", *order, "healthy_after_rollback"]
    for i, scenario in enumerate(plan):
        gen_name = "healthy" if scenario == "healthy_after_rollback" else scenario
        if scenario == "healthy_after_rollback":
            champion = first_champion
        batch = gen.generate_scenario(gen_name, seed + 17 * (i + 1), settings.expected_volume)
        if healthy_ref is None:
            healthy_ref = batch
        rec = {
            "perm_id": perm_id,
            "seed": seed,
            "order": list(order),
            "scenario": scenario,
            "n_rows": len(batch),
            "psi_mean": round(mean_psi(healthy_ref, batch), 4),
            "drift_level": drift_level(mean_psi(healthy_ref, batch)),
            "champion_context": champion_context(drift_promoted, champion, first_champion),
            "champion_f1": None if champion is None else round(champion.get("f1", 0), 4),
            "outcome": None,
            "f1": None,
            "accuracy": None,
            "regression_pct": None,
            "reasons": None,
        }
        if not volume_ok(len(batch)):
            rec["outcome"] = "BLOCKED"
            log.info("  %s BLOCKED", scenario)
            rows.append(rec)
            continue
        metrics = train_mlp(batch, seed + 100 * (i + 1))
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
            if scenario == "feature_drift":
                drift_promoted = True
        log.info(
            "  %s %s F1=%s ctx=%s champ=%s",
            scenario, outcome, rec["f1"], rec["champion_context"], rec["champion_f1"],
        )
        rows.append(rec)
    return rows


def wilson(k: int, n: int) -> list[float]:
    if n == 0:
        return [0.0, 0.0, 0.0]
    z = 1.96
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / den
    return [round(k / n, 4), round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4)]


def summarize(rows: list[dict]) -> dict:
    stress = [r for r in rows if r["scenario"] in ("label_imbalance", "regression")]
    out = {}
    for scenario in ("label_imbalance", "regression"):
        items = [r for r in stress if r["scenario"] == scenario]
        by_ctx = {"post_drift": [], "first_healthy": [], "other": []}
        for r in items:
            by_ctx.setdefault(r["champion_context"], []).append(r)
        cell = {}
        for ctx, group in by_ctx.items():
            n = len(group)
            rej = sum(1 for r in group if r["outcome"] == "REJECTED")
            pro = sum(1 for r in group if r["outcome"] == "PROMOTED")
            cell[ctx] = {
                "n": n,
                "rejected": rej,
                "promoted": pro,
                "reject_rate_wilson": wilson(rej, n),
                "promotions": [
                    {
                        "perm_id": r["perm_id"],
                        "order": r["order"],
                        "f1": r["f1"],
                        "champion_f1": r["champion_f1"],
                        "regression_pct": r["regression_pct"],
                        "accuracy": r["accuracy"],
                    }
                    for r in group if r["outcome"] == "PROMOTED"
                ],
            }
        out[scenario] = cell
    drift = [r for r in rows if r["scenario"] == "feature_drift"]
    volume = [r for r in rows if r["scenario"] == "volume_anomaly"]
    out["feature_drift_promoted"] = sum(1 for r in drift if r["outcome"] == "PROMOTED")
    out["feature_drift_n"] = len(drift)
    out["volume_blocked"] = sum(1 for r in volume if r["outcome"] == "BLOCKED")
    out["volume_n"] = len(volume)
    return out


def main() -> None:
    orders = list(permutations(STRESS))
    rows = []
    for perm_id, order in enumerate(orders):
        rows.extend(run_one(perm_id, order))
    summary = summarize(rows)
    blob = {
        "family": "8-16-8-1 MLP (same trainer as Table 6)",
        "note": (
            "All 24 permutations of the four stress scenarios. Healthy opener and "
            "rollback coda fixed. Rollback after all stress, matching Table 7. "
            "n=1 seed per permutation. Exploratory; not used to rescore H1-H3."
        ),
        "n_permutations": len(orders),
        "n_runs": len(rows),
        "orders": [list(o) for o in orders],
        "summary": summary,
        "rows": rows,
    }
    OUT.write_text(json.dumps(blob, indent=2) + "\n")
    print(json.dumps({"n_permutations": len(orders), "n_runs": len(rows), "summary": summary}, indent=2))


if __name__ == "__main__":
    main()
