"""Within-order replicates of four pre-specified Table 14 orders (MLP).

Table 14 covered all 24 permutations at n=1. This run repeats four orders
at n=5 new seeds each. Arms were chosen before these seeds ran:

  leak18   — perm 18 (regression first); the Table 14 regression promotion
  miss19   — perm 19 (regression, volume, imbalance, drift); the Table 14
             drift miss on the recall-versus-champion clause
  planned  — perm 0 (volume, drift, imbalance, regression); post-drift
             regression control, same stress order as Table 6
  first_reg — perm 4 (volume, regression, drift, imbalance); another
              first-healthy regression cell that is not perm 18

New seeds 9601+. Does not touch confirmatory registry names. In-process.
Not pooled with Table 14. Not used to rescore H1-H3.
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
log = logging.getLogger("order-replicates")

ARMS = {
    "leak18": {
        "perm_id": 18,
        "order": ("regression", "volume_anomaly", "feature_drift", "label_imbalance"),
        "seeds": [9601, 9602, 9603, 9604, 9605],
        "why": "Table 14's single regression promotion (first-healthy)",
    },
    "miss19": {
        "perm_id": 19,
        "order": ("regression", "volume_anomaly", "label_imbalance", "feature_drift"),
        "seeds": [9611, 9612, 9613, 9614, 9615],
        "why": "Table 14's single drift miss (recall-versus-champion)",
    },
    "planned": {
        "perm_id": 0,
        "order": ("volume_anomaly", "feature_drift", "label_imbalance", "regression"),
        "seeds": [9621, 9622, 9623, 9624, 9625],
        "why": "Post-drift regression control; confirmatory stress order",
    },
    "first_reg": {
        "perm_id": 4,
        "order": ("volume_anomaly", "regression", "feature_drift", "label_imbalance"),
        "seeds": [9631, 9632, 9633, 9634, 9635],
        "why": "First-healthy regression cell that is not perm 18",
    },
}
OUT = Path("/tmp/order-replicates.json")


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


def run_one(arm: str, seed: int, order: tuple[str, ...]) -> list[dict]:
    log.info("arm=%s seed=%s order=%s", arm, seed, ",".join(order))
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
            "arm": arm,
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
            "precision": None,
            "recall": None,
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
    out = {}
    for arm in ARMS:
        items = [r for r in rows if r["arm"] == arm]
        cell = {}
        for scenario in ("healthy", "volume_anomaly", "feature_drift", "label_imbalance", "regression", "healthy_after_rollback"):
            group = [r for r in items if r["scenario"] == scenario]
            f1s = [r["f1"] for r in group if r["f1"] is not None]
            cell[scenario] = {
                "n": len(group),
                "outcomes": {
                    k: sum(1 for r in group if r["outcome"] == k)
                    for k in ("PROMOTED", "REJECTED", "BLOCKED")
                },
                "mean_f1": round(float(np.mean(f1s)), 4) if f1s else None,
                "champion_contexts": sorted({r["champion_context"] for r in group}),
                "promotions": [
                    {
                        "seed": r["seed"],
                        "f1": r["f1"],
                        "champion_f1": r["champion_f1"],
                        "regression_pct": r["regression_pct"],
                        "accuracy": r["accuracy"],
                        "recall": r["recall"],
                        "reasons": r["reasons"],
                    }
                    for r in group if r["outcome"] == "PROMOTED"
                ],
                "rejects": [
                    {
                        "seed": r["seed"],
                        "f1": r["f1"],
                        "champion_f1": r["champion_f1"],
                        "regression_pct": r["regression_pct"],
                        "recall": r["recall"],
                        "reasons": r["reasons"],
                    }
                    for r in group if r["outcome"] == "REJECTED"
                ],
            }
        out[arm] = cell
    first_healthy_reg = [
        r for r in rows
        if r["scenario"] == "regression" and r["champion_context"] == "first_healthy"
    ]
    post_drift_reg = [
        r for r in rows
        if r["scenario"] == "regression" and r["champion_context"] == "post_drift"
    ]
    out["pooled_regression"] = {
        "first_healthy": {
            "n": len(first_healthy_reg),
            "promoted": sum(1 for r in first_healthy_reg if r["outcome"] == "PROMOTED"),
            "rejected": sum(1 for r in first_healthy_reg if r["outcome"] == "REJECTED"),
            "reject_rate_wilson": wilson(
                sum(1 for r in first_healthy_reg if r["outcome"] == "REJECTED"),
                len(first_healthy_reg),
            ),
        },
        "post_drift": {
            "n": len(post_drift_reg),
            "promoted": sum(1 for r in post_drift_reg if r["outcome"] == "PROMOTED"),
            "rejected": sum(1 for r in post_drift_reg if r["outcome"] == "REJECTED"),
            "reject_rate_wilson": wilson(
                sum(1 for r in post_drift_reg if r["outcome"] == "REJECTED"),
                len(post_drift_reg),
            ),
        },
    }
    return out


def main() -> None:
    rows = []
    for arm, spec in ARMS.items():
        for seed in spec["seeds"]:
            rows.extend(run_one(arm, seed, spec["order"]))
    summary = summarize(rows)
    blob = {
        "family": "8-16-8-1 MLP (same trainer as Tables 6 and 14)",
        "note": (
            "Four pre-specified Table 14 orders at n=5 new seeds. "
            "Not a full 24-order replicate. Not pooled with Table 14. "
            "Exploratory; not used to rescore H1-H3."
        ),
        "arms": {k: {"perm_id": v["perm_id"], "order": list(v["order"]), "seeds": v["seeds"], "why": v["why"]} for k, v in ARMS.items()},
        "n_arms": len(ARMS),
        "n_seeds_per_arm": 5,
        "n_runs": len(rows),
        "summary": summary,
        "rows": rows,
    }
    OUT.write_text(json.dumps(blob, indent=2) + "\n")
    print(json.dumps({
        "n_runs": len(rows),
        "pooled_regression": summary["pooled_regression"],
        "arms": {
            arm: {
                "regression": summary[arm]["regression"]["outcomes"],
                "feature_drift": summary[arm]["feature_drift"]["outcomes"],
                "label_imbalance": summary[arm]["label_imbalance"]["outcomes"],
            }
            for arm in ARMS
        },
    }, indent=2))


if __name__ == "__main__":
    main()
