"""Score live ablation arms from the API. Writes live-ablation.json."""
import json
import urllib.request
from pathlib import Path

API = "http://127.0.0.1:8166"
OUT = Path(__file__).resolve().parents[1] / "k8s" / "metrics" / "live-ablation.json"
ARMS = {
    "accuracy_only": [f"churn-predictor-acc{i}" for i in range(1, 6)],
    "floors_only": [f"churn-predictor-floors{i}" for i in range(1, 6)],
}


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
    if trig == "manual" or "re-run after rollback" in detail:
        return "healthy_after_rollback"
    if "experiment 1" in detail or "baseline" in detail:
        return "healthy"
    if trig == "schedule":
        return "label_imbalance"
    return "?"


def main() -> None:
    blob = {"note": "Live promotions under swapped gates. Confirmatory Table 6 used full Algorithm 1.", "arms": {}}
    for arm, names in ARMS.items():
        by = {}
        rows = []
        for name in names:
            hist = list(reversed(get(f"/api/v1/models/{name}/training/history?limit=20")))
            rec = {"model": name}
            for run in hist:
                sc = scenario_of(run)
                rec[sc] = run.get("outcome") or run.get("status")
                rec[f"{sc}_f1"] = (run.get("candidate") or {}).get("test_f1") if False else None
            # candidate not in history serializer — pull evaluation when possible
            for run in hist:
                sc = scenario_of(run)
                if run.get("status") == "BLOCKED":
                    continue
                try:
                    ev = get(f"/api/v1/models/{name}/evaluation/{run['id']}")
                    rec[f"{sc}_f1"] = (ev.get("candidate_metrics") or {}).get("f1")
                    rec[f"{sc}_acc"] = (ev.get("candidate_metrics") or {}).get("accuracy")
                    rec[f"{sc}_gate"] = ev.get("gate_result")
                except Exception:
                    pass
            rows.append(rec)
            for sc in ("healthy", "volume_anomaly", "feature_drift", "label_imbalance", "regression", "healthy_after_rollback"):
                by.setdefault(sc, {"PROMOTED": 0, "MODEL_NOT_PROMOTED": 0, "DATA_VOLUME_ALERT": 0, "other": 0})
                oc = rec.get(sc) or ""
                if oc in by[sc]:
                    by[sc][oc] += 1
                elif oc:
                    by[sc]["other"] += 1
        blob["arms"][arm] = {"n": len(names), "by_scenario": by, "rows": rows}
    OUT.write_text(json.dumps(blob, indent=2) + "\n")
    for arm, data in blob["arms"].items():
        print(arm, json.dumps(data["by_scenario"], indent=2))


if __name__ == "__main__":
    main()
