"""Summarize the Section 8.4 joint-predicate snapshot."""
import json
from collections import defaultdict
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "k8s" / "metrics" / "section-84.json"


def main() -> None:
    blob = json.loads(SRC.read_text())
    groups = defaultdict(list)
    for row in blob["rows"]:
        groups[row["scenario"]].append(row)
    print(f"joint_fires {blob['joint_fires']} / {blob['n_scenario_cells']}")
    print("scenario n fire drift ev cell psi_mean champ_f1")
    for scenario, rows in groups.items():
        n = len(rows)
        fire = sum(1 for r in rows if r["joint_retrain"])
        drift = ",".join(sorted({r["drift_level"] for r in rows}))
        ev = ",".join(sorted({r["evaluation_level"] for r in rows}))
        cell = ",".join(sorted({r["matrix_cell"] for r in rows}))
        psi = sum(r["psi_mean"] for r in rows) / n
        f1 = sum(r["champion_f1_on_batch"] for r in rows) / n
        print(f"{scenario:16} {n} {fire}/{n} {drift:12} {ev:8} {cell:20} {psi:.3f} {f1:.3f}")


if __name__ == "__main__":
    main()
