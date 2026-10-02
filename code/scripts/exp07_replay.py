"""EXP-07 — decision-lineage replay.

Connects to the live Postgres instance (the same one the backend container
uses, via its host-exposed port), reconstructs every persisted JointDecision
and EvaluationResult row, and replays it through the real policy.py / gates.py
functions. Reports a match rate -- any mismatch is reported, not hidden
(P6-05 no-result policy).

Run from the host (not the container) against docker-compose's exposed
postgres port:

    PYTHONPATH=backend python scripts/exp07_replay.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.ml import decision_record
from app import models as m  # noqa: F401

HOST_DATABASE_URL = "postgresql+psycopg2://dact_user:dact_pass@localhost:5476/dact_training"
OUT = Path(__file__).resolve().parents[1] / "evidence" / "exp07_replay.json"


def _provenance() -> dict:
    try:
        import subprocess
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path(__file__).resolve().parents[1], text=True,
        ).strip()
    except Exception:
        commit = "unknown"
    return {"experiment_id": "EXP-07", "git_commit": commit, "timestamp": datetime.now(timezone.utc).isoformat()}


def main() -> None:
    engine = create_engine(HOST_DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        result = decision_record.replay_all(db)
    finally:
        db.close()

    blob = {**_provenance(), **result}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(blob, indent=2, default=str) + "\n")
    print(json.dumps({k: v for k, v in blob.items() if k not in ("joint_decisions", "evaluation_results")}, indent=2))
    if result["mismatched"]:
        print(f"\n{result['mismatched']} MISMATCH(ES):")
        for r in result["joint_decisions"] + result["evaluation_results"]:
            if not r["match"]:
                print(" ", r)


if __name__ == "__main__":
    main()
