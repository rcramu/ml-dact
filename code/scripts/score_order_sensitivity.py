"""Score Arm A vs Arm B from the live API. Writes order-sensitivity.json."""
import json
import math
import urllib.request
from pathlib import Path

API = "http://127.0.0.1:8166"
OUT = Path(__file__).resolve().parents[1] / "k8s" / "metrics" / "order-sensitivity.json"

ARM_A = {
    "churn-predictor-ord1": ["volume_anomaly", "feature_drift", "label_imbalance", "regression"],
    "churn-predictor-ord2": ["feature_drift", "volume_anomaly", "regression", "label_imbalance"],
    "churn-predictor-ord5": ["feature_drift", "regression", "label_imbalance", "volume_anomaly"],
    "churn-predictor-a4": ["volume_anomaly", "feature_drift", "regression", "label_imbalance"],
    "churn-predictor-a5": ["feature_drift", "volume_anomaly", "label_imbalance", "regression"],
    "churn-predictor-a6": ["feature_drift", "label_imbalance", "regression", "volume_anomaly"],
    "churn-predictor-a7": ["feature_drift", "label_imbalance", "volume_anomaly", "regression"],
    "churn-predictor-a8": ["volume_anomaly", "feature_drift", "label_imbalance", "regression"],
    "churn-predictor-a9": ["feature_drift", "regression", "volume_anomaly", "label_imbalance"],
    "churn-predictor-a10": ["feature_drift", "volume_anomaly", "regression", "label_imbalance"],
}
ARM_B = {
    "churn-predictor-ord3": ["regression", "label_imbalance", "volume_anomaly", "feature_drift"],
    "churn-predictor-ord4": ["label_imbalance", "regression", "feature_drift", "volume_anomaly"],
    "churn-predictor-b3": ["regression", "label_imbalance", "feature_drift", "volume_anomaly"],
    "churn-predictor-b4": ["label_imbalance", "regression", "volume_anomaly", "feature_drift"],
    "churn-predictor-b5": ["regression", "volume_anomaly", "label_imbalance", "feature_drift"],
    "churn-predictor-b6": ["label_imbalance", "volume_anomaly", "regression", "feature_drift"],
    "churn-predictor-b7": ["volume_anomaly", "regression", "label_imbalance", "feature_drift"],
    "churn-predictor-b8": ["volume_anomaly", "label_imbalance", "regression", "feature_drift"],
    "churn-predictor-b9": ["regression", "label_imbalance", "volume_anomaly", "feature_drift"],
    "churn-predictor-b10": ["label_imbalance", "regression", "feature_drift", "volume_anomaly"],
}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    if n <= 0:
        return 0.0, 0.0, 0.0
    p = k / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return p, (centre - spread) / denom, (centre + spread) / denom


def get(path: str):
    with urllib.request.urlopen(API + path, timeout=30) as r:
        return json.load(r)


def scenario_of(run: dict) -> str:
    detail = (run.get("trigger_detail") or "").lower()
    trig = run.get("trigger_type")
    if trig == "data_availability" or "volume" in detail:
        return "volume_anomaly"
    if trig == "drift" or "feature drift" in detail:
        return "feature_drift"
    if trig == "performance" or ("regression" in detail and "rollback" not in detail):
        return "regression"
    if trig == "manual" or "rollback" in detail:
        return "healthy_after_rollback"
    if "opener" in detail or "baseline" in detail:
        return "healthy"
    if trig == "schedule":
        return "label_imbalance" if "weekly" in detail else "healthy"
    return "?"


def score_arm(models: dict, arm: str) -> list[dict]:
    rows = []
    for name, order in models.items():
        hist = list(reversed(get(f"/api/v1/models/{name}/training/history?limit=20")))
        rec = {"model": name, "arm": arm, "order": order}
        for run in hist:
            sc = scenario_of(run)
            rec[sc] = run.get("outcome") or run.get("status")
            if sc in ("label_imbalance", "regression") and run.get("status") != "BLOCKED":
                try:
                    ev = get(f"/api/v1/models/{name}/evaluation/{run['id']}")
                    rec[f"{sc}_f1"] = (ev.get("candidate_metrics") or {}).get("f1")
                    rec[f"{sc}_champ_f1"] = (ev.get("champion_metrics") or {}).get("f1")
                    rec[f"{sc}_regpct"] = ev.get("regression_pct")
                    rec[f"{sc}_reasons"] = ev.get("reasons")
                except Exception:
                    pass
        rows.append(rec)
    return rows


def count(rows, scenario, outcome_substr):
    return sum(1 for r in rows if outcome_substr in str(r.get(scenario, "")))


def main() -> None:
    a = score_arm(ARM_A, "A")
    b = score_arm(ARM_B, "B")
    a_reg_rej = count(a, "regression", "NOT_PROMOTED")
    b_reg_rej = count(b, "regression", "NOT_PROMOTED")
    a_imb_rej = count(a, "label_imbalance", "NOT_PROMOTED")
    b_imb_rej = count(b, "label_imbalance", "NOT_PROMOTED")
    a_n, b_n = len(a), len(b)
    blob = {
        "purpose": "Exploratory H3 order sensitivity. Not a replacement for Table 6.",
        "n_per_arm": {"A": a_n, "B": b_n},
        "imbalance_reject": {
            "A": f"{a_imb_rej}/{a_n}",
            "B": f"{b_imb_rej}/{b_n}",
            "B_wilson": list(wilson(b_imb_rej, b_n)),
        },
        "regression_reject": {
            "A": f"{a_reg_rej}/{a_n}",
            "B": f"{b_reg_rej}/{b_n}",
            "A_wilson": list(wilson(a_reg_rej, a_n)),
            "B_wilson": list(wilson(b_reg_rej, b_n)),
        },
        "rows": a + b,
    }
    OUT.write_text(json.dumps(blob, indent=2) + "\n")
    print(json.dumps({k: blob[k] for k in blob if k != "rows"}, indent=2))
    print("wrote", OUT)
    print("Arm A regression rejects", a_reg_rej, "/", a_n)
    print("Arm B regression rejects", b_reg_rej, "/", b_n)
    for r in b:
        print(" B", r["model"], "reg", r.get("regression"), "imb", r.get("label_imbalance"))


if __name__ == "__main__":
    main()
