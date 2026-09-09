"""Trigger electricity_joint_dag on kind for folds 0..4.

Uses kubectl --context kind-dact-local-eks. Does not print secrets.
Confirmatory model names are never passed to the DAG.
"""
import json
import re
import subprocess
import time
from pathlib import Path

CTX = ["kubectl", "--context", "kind-dact-local-eks", "-n", "dact"]
FOLDS = [0, 1, 2, 3, 4]
OUT = Path("/tmp/electricity-live-airflow.json")


def run(args: list[str], timeout: int = 180) -> str:
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


def wait_dag_run(run_id: str, timeout: int = 600) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        out = scheduler_exec(
            ["airflow", "dags", "list-runs", "-d", "electricity_joint_dag", "-o", "plain"],
            timeout=60,
        )
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[1] == run_id and parts[2] in {"success", "failed"}:
                return parts[2]
        time.sleep(5)
    return "timeout"


def main() -> None:
    scheduler_exec(["airflow", "dags", "unpause", "electricity_joint_dag"])
    rows = []
    for fold in FOLDS:
        print(f"trigger electricity-joint fold={fold}", flush=True)
        out = scheduler_exec([
            "airflow", "dags", "trigger", "electricity_joint_dag",
            "--conf", json.dumps({"fold": fold}),
        ])
            match = re.search(r"(manual__\S+)", out)
            run_id = match.group(1).rstrip(".,;:") if match else None
            if run_id is None:
                runs = scheduler_exec(["airflow", "dags", "list-runs", "-d", "electricity_joint_dag", "-o", "plain"])
                run_id = runs.strip().splitlines()[-1].split()[1]
        state = wait_dag_run(run_id)
        decision = api(f"/api/v1/electricity/joint-cell?fold={fold}")
        history = api("/api/v1/models/electricity-joint/training/history?limit=20")
        marker = f"fold={fold}"
        matched = next(
            (h for h in history if marker in str(h.get("trigger_detail") or "")),
            None,
        )
        rec = {
            "fold": fold,
            "dag_run_id": run_id,
            "dag_state": state,
            "decision": decision,
            "latest_trigger_type": None if matched is None else matched.get("trigger_type"),
            "latest_outcome": None if matched is None else matched.get("outcome"),
            "latest_status": None if matched is None else matched.get("status"),
        }
        print(
            f"  {state} {decision.get('drift_level')} x {decision.get('evaluation_level')} "
            f"fire={decision.get('joint_retrain')} trigger={rec['latest_trigger_type']} "
            f"outcome={rec['latest_outcome']}",
            flush=True,
        )
        rows.append(rec)
    fires = sum(1 for r in rows if r["decision"].get("joint_retrain"))
    trained = sum(1 for r in rows if r["latest_trigger_type"] == "joint")
    blob = {
        "note": (
            "Live Airflow electricity_joint_dag. Exploratory electricity-joint only. "
            "Not used to rescore H1-H3. Confirmatory names were not triggered. "
            "Candidates are trained only on fire."
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
