"""Retrospective Algorithm 1 threshold sweep on confirmatory stored metrics.

Does not train. Sweeps F1_min and MaxRegression% on the 13 rejected + the
12 promoted candidates so we can see both false-pass and false-block risk.
"""
from __future__ import annotations

import json
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "k8s" / "metrics" / "replicates.json"
OUT = Path(__file__).resolve().parents[1] / "k8s" / "metrics" / "threshold-sweep.json"
P_MIN, R_MIN = 0.60, 0.60
F1_GRID = (0.60, 0.65, 0.70, 0.75, 0.80)
REG_GRID = (5.0, 10.0, 15.0)


def decide(c: dict, champ: dict | None, f1_min: float, max_reg: float) -> bool:
    if c["test_f1"] < f1_min or c["precision"] < P_MIN or c["recall"] < R_MIN:
        return False
    if champ and champ["test_f1"] > 0:
        reg = ((champ["test_f1"] - c["test_f1"]) / champ["test_f1"]) * 100
        if reg > max_reg:
            return False
        if c["recall"] < champ["recall"]:
            return False
    return True


def candidates() -> list[dict]:
    data = json.loads(SRC.read_text())
    out = []
    for model in data["models"]:
        champ = None
        first_healthy = None
        for run in model["runs"]:
            cand = run.get("candidate")
            if run["status"] == "BLOCKED":
                continue
            champ_now = first_healthy if run["scenario"] == "healthy_after_rollback" and first_healthy else champ
            if cand:
                out.append(
                    {
                        "model": model["name"],
                        "scenario": run["scenario"],
                        "outcome": run["outcome"],
                        "cand": cand,
                        "champ": champ_now,
                    }
                )
            if run["status"] == "SUCCESS" and run["outcome"] == "PROMOTED" and cand:
                champ = cand
                if run["scenario"] == "healthy":
                    first_healthy = cand
    return out


def main() -> None:
    rows = candidates()
    grid = []
    for f1_min in F1_GRID:
        for max_reg in REG_GRID:
            would_pass = [r for r in rows if decide(r["cand"], r["champ"], f1_min, max_reg)]
            published_pass = [r for r in rows if r["outcome"] == "PROMOTED"]
            published_fail = [r for r in rows if r["outcome"] == "MODEL_NOT_PROMOTED"]
            false_pass = [r for r in published_fail if decide(r["cand"], r["champ"], f1_min, max_reg)]
            false_block = [r for r in published_pass if not decide(r["cand"], r["champ"], f1_min, max_reg)]
            cell = {
                "f1_min": f1_min,
                "max_regression_pct": max_reg,
                "would_pass": len(would_pass),
                "published_pass": len(published_pass),
                "published_fail": len(published_fail),
                "false_pass_of_published_rejects": len(false_pass),
                "false_block_of_published_promotes": len(false_block),
                "false_pass_scenarios": [r["scenario"] for r in false_pass],
                "false_block_scenarios": [r["scenario"] for r in false_block],
            }
            grid.append(cell)
    blob = {
        "note": "Retrospective sweep on stored test metrics. Not a live retrain.",
        "n_trained": len(rows),
        "p_min": P_MIN,
        "r_min": R_MIN,
        "published": {"f1_min": 0.70, "max_regression_pct": 10.0},
        "grid": grid,
    }
    OUT.write_text(json.dumps(blob, indent=2) + "\n")
    print(json.dumps(blob, indent=2))


if __name__ == "__main__":
    main()
