#!/usr/bin/env python3
"""Export the paper's synthetic churn datasets into code/data/ for version control.

Uses the same generator and documented seeds as the reference implementation
(Section 7.1). No personal data. Deterministic and check-in safe.
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.data_generator import FEATURE_NAMES, generate_scenario  # noqa: E402

OUT = ROOT / "data"

# Documented, fixed seeds so a checked-in CSV matches a later regeneration.
SCENARIOS = [
    ("healthy", 42, 1500, "S — stable / no injected drift; P_train(X) ~ P_prod(X)"),
    ("feature_drift", 43, 1500, "M/V — satisfaction and usage_score shifted (paper feature_drift)"),
    ("volume_anomaly", 44, 1500, "Operational: ~12% of expected rows"),
    ("label_imbalance", 45, 1500, "Churn forced to ~2% (accuracy-paradox / rare-event case)"),
    ("regression", 46, 1500, "Heavy label noise so a candidate should fail the gate"),
]

COLUMNS = ["customer_id", "scenario", "split", *FEATURE_NAMES, "churn"]


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def to_rows(scenario: str, records: list[dict], start_id: int) -> list[dict]:
    out = []
    for i, rec in enumerate(records):
        out.append({
            "customer_id": f"{scenario}-{start_id + i:05d}",
            "scenario": scenario,
            "split": rec["split"],
            "age": rec["age"],
            "tenure_days": rec["tenure_days"],
            "monthly_charges": rec["monthly_charges"],
            "support_tickets": rec["support_tickets"],
            "usage_score": rec["usage_score"],
            "service_count": rec["service_count"],
            "customer_satisfaction": rec["customer_satisfaction"],
            "is_month_to_month": int(rec["is_month_to_month"]),
            "churn": rec["label"],
        })
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "backend/app/data_generator.py",
        "license": "synthetic — no personal data — generated for this paper",
        "features": FEATURE_NAMES,
        "label": "churn",
        "split": "70/15/15 train/val/test (row-level 'split' column)",
        "scenarios": [],
    }
    combined: list[dict] = []
    for name, seed, n, description in SCENARIOS:
        records = generate_scenario(name, seed, n)
        rows = to_rows(name, records, 1)
        write_csv(OUT / f"{name}.csv", rows)
        combined.extend(rows)
        churn = sum(r["churn"] for r in rows)
        manifest["scenarios"].append({
            "id": name,
            "file": f"{name}.csv",
            "seed": seed,
            "requested_rows": n,
            "rows": len(rows),
            "churn_count": churn,
            "churn_rate": round(churn / max(len(rows), 1), 4),
            "description": description,
        })
    write_csv(OUT / "churn_all_scenarios.csv", combined)
    schema = {
        "customer_id": "synthetic identifier, not a real person",
        "scenario": "generator scenario id",
        "split": "train | val | test",
        "age": "integer years",
        "tenure_days": "integer",
        "monthly_charges": "float",
        "support_tickets": "integer count",
        "usage_score": "float 0-1",
        "service_count": "integer",
        "customer_satisfaction": "float 0-1",
        "is_month_to_month": "0/1",
        "churn": "binary label 0/1",
    }
    (OUT / "schema.json").write_text(json.dumps(schema, indent=2) + "\n")
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Wrote {len(SCENARIOS) + 1} CSV files + schema/manifest under {OUT}")


if __name__ == "__main__":
    main()
