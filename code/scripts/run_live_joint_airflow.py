"""Trigger joint_retrain_dag on kind for five exploratory models.

Uses kubectl --context kind-dact-local-eks. Does not print secrets.
Confirmatory model names are never passed to the DAG.
"""
import json
import re
import subprocess
import time
from pathlib import Path

CTX = ["kubectl", "--context", "kind-dact-local-eks", "-n", "dact"]
MODELS = [f"churn-predictor-joint{i}" for i in range(1, 6)]
SEEDS = [9801, 9802, 9803, 9804, 9805]
SCENARIOS = [
    "healthy",
    "volume_anomaly",
    "feature_drift",
    "label_imbalance",
    "regression",
]
SEED_OFF = {
    "healthy": 0,
    "volume_anomaly": 17,
    "feature_drift": 34,
    "label_imbalance": 51,
    "regression": 68,
}
OUT = Path("/tmp/live-joint-airflow.json")


def run(args: list[str], timeout: int = 120) -> str:
    proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or f"exit {proc.returncode}")
    return proc.stdout


def scheduler_exec(args: list[str], timeout: int = 180) -> str:
    return run(CTX + ["exec", "deploy/airflow-scheduler", "--"] + args, timeout=timeout)


def api(path: str) -> dict | list:
    raw = run(CTX + ["exec", "deploy/backend", "--", "python", "-c",
                     f"import json,urllib.request; print(json.dumps(json.load(urllib.request.urlopen('http://127.0.0.1:8000{path}'))))"])
    return json.loads(raw)


def wait_dag_run(run_id: str, timeout: int = 360) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        out = scheduler_exec(
            ["airflow", "dags", "list-runs", "-d", "joint_retrain_dag", "-o", "plain"],
            timeout=60,
        )
        for line in out.splitlines():
            if run_id in line:
                parts = line.split()
                if len(parts) >= 3 and parts[2] in {"success", "failed"}:
                    return parts[2]
        time.sleep(4)
    return "timeout"


def main() -> None:
    scheduler_exec(["airflow", "dags", "unpause", "joint_retrain_dag"])
    rows = []
    for model, seed in zip(MODELS, SEEDS):
        for scenario in SCENARIOS:
            cell_seed = seed + SEED_OFF[scenario]
            print(f"trigger {model} {scenario} seed={cell_seed}", flush=True)
            out = scheduler_exec([
                "airflow", "dags", "trigger", "joint_retrain_dag",
                "--conf", json.dumps({"model": model, "scenario": scenario, "seed": cell_seed}),
            ])
            match = re.search(r"manual__\S+", out)
            run_id = match.group(0) if match else None
            if run_id is None:
                runs = scheduler_exec(["airflow", "dags", "list-runs", "-d", "joint_retrain_dag", "-o", "plain"])
                run_id = runs.strip().splitlines()[-1].split()[1]
            state = wait_dag_run(run_id)
            decision = api(f"/api/v1/models/{model}/joint-cell?scenario={scenario}&seed={cell_seed}")
            history = api(f"/api/v1/models/{model}/training/history?limit=5")
            latest = history[0] if history else None
            rec = {
                "model": model,
                "scenario": scenario,
                "dag_run_id": run_id,
                "dag_state": state,
                "decision": decision,
                "latest_trigger_type": None if latest is None else latest.get("trigger_type"),
                "latest_outcome": None if latest is None else latest.get("outcome"),
                "latest_status": None if latest is None else latest.get("status"),
            }
            print(
                f"  {state} {decision.get('drift_level')} x {decision.get('evaluation_level')} "
                f"fire={decision.get('joint_retrain')} trigger={rec['latest_trigger_type']}",
                flush=True,
            )
            rows.append(rec)
    fires = sum(1 for r in rows if r["decision"].get("joint_retrain"))
    trained = sum(1 for r in rows if r["latest_trigger_type"] == "joint")
    blob = {
        "note": (
            "Live Airflow joint_retrain_dag. Exploratory models only. "
            "Not used to rescore H1-H3. Confirmatory names were not triggered."
        ),
        "n_cells": len(rows),
        "joint_fires": fires,
        "joint_trained": trained,
        "dag_success": sum(1 for r in rows if r["dag_state"] == "success"),
        "rows": rows,
    }
    OUT.write_text(json.dumps(blob, indent=2) + "\n")
    print(json.dumps({k: blob[k] for k in blob if k != "rows"}, indent=2))


if __name__ == "__main__":
    main()
