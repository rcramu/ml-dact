"""Retrospective Algorithm 1 ablation on the 13 rejected candidates in replicates.json.

This re-applies gate variants to stored metrics. It does not train new models.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "code" / "k8s" / "metrics" / "replicates.json"

F1_MIN, P_MIN, R_MIN, MAX_REG = 0.70, 0.60, 0.60, 10.0
NAMES = {
    "churn-predictor": "r1",
    "churn-predictor-r2": "r2",
    "churn-predictor-r3": "r3",
    "churn-predictor-r4": "r4",
    "churn-predictor-r5": "r5",
}


def floors(c: dict) -> bool:
    return c["test_f1"] >= F1_MIN and c["precision"] >= P_MIN and c["recall"] >= R_MIN


def accuracy_only(c: dict) -> bool:
    return c["accuracy"] >= F1_MIN


def full_gate(c: dict, champ: dict | None) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if c["test_f1"] < F1_MIN:
        reasons.append("F1")
    if c["precision"] < P_MIN:
        reasons.append("P")
    if c["recall"] < R_MIN:
        reasons.append("R")
    if champ and champ["test_f1"] > 0:
        reg = ((champ["test_f1"] - c["test_f1"]) / champ["test_f1"]) * 100
        if reg > MAX_REG:
            reasons.append(f"reg{reg:.1f}")
        if c["recall"] < champ["recall"]:
            reasons.append("R<champ")
    return len(reasons) == 0, reasons


def rows() -> list[dict]:
    data = json.loads(SRC.read_text())
    out: list[dict] = []
    for model in data["models"]:
        champ = None
        first_healthy = None
        for run in model["runs"]:
            cand = run.get("candidate")
            if run["status"] == "SUCCESS" and run["outcome"] == "PROMOTED" and cand:
                champ = cand
                if run["scenario"] == "healthy":
                    first_healthy = cand
            champ_now = first_healthy if run["scenario"] == "healthy_after_rollback" and first_healthy else champ
            if run["status"] == "REJECTED" and cand:
                passed, reasons = full_gate(cand, champ_now)
                out.append(
                    {
                        "seed": NAMES[model["name"]],
                        "scenario": run["scenario"],
                        "accuracy_only": accuracy_only(cand),
                        "floors_only": floors(cand),
                        "full": passed,
                        "reasons": reasons,
                    }
                )
    return out


def summary(records: list[dict]) -> dict:
    by = defaultdict(lambda: {"n": 0, "acc": 0, "floors": 0, "full": 0})
    totals = {"n": 0, "acc": 0, "floors": 0, "full": 0}
    for row in records:
        sc = row["scenario"]
        by[sc]["n"] += 1
        by[sc]["acc"] += int(row["accuracy_only"])
        by[sc]["floors"] += int(row["floors_only"])
        by[sc]["full"] += int(row["full"])
        totals["n"] += 1
        totals["acc"] += int(row["accuracy_only"])
        totals["floors"] += int(row["floors_only"])
        totals["full"] += int(row["full"])
    return {"by_scenario": dict(by), "totals": totals}


if __name__ == "__main__":
    records = rows()
    print(json.dumps(summary(records), indent=2))
