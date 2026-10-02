"""MEDP retrain-trigger policy (Section 8.4 joint cell).

Single source of truth for the drift x incumbent-health decision matrix that
was previously copy-pasted across ``routers/joint.py``, ``ml/electricity.py``,
and ``scripts/run_electricity_natural.py``. Extracted verbatim (not
reimplemented) so EXP-06's policy tests exercise the real production decision,
and so the three call sites cannot drift out of sync with each other.

``DriftLevel`` comes from :func:`app.ml.drift.drift_level` (NORMAL/WARNING/
SIGNIFICANT). ``EvaluationLevel`` is GOOD iff the current champion's F1 on a
fresh batch is >= the F1 floor, BAD otherwise, UNKNOWN when there isn't enough
test data (or no champion) to score it.
"""
from __future__ import annotations

from typing import Literal

EvaluationLevel = Literal["GOOD", "BAD", "UNKNOWN"]
DriftLevel = Literal["NORMAL", "WARNING", "SIGNIFICANT"]
TriggerState = Literal["RETAIN", "EVALUATE", "RETRAIN"]

#: The exact 9-entry matrix previously duplicated in joint.py/_cell,
#: ml/electricity.py/cell, and scripts/run_electricity_natural.py/cell.
CELL_TABLE: dict[tuple[str, str], str] = {
    ("NORMAL", "GOOD"): "Continue",
    ("NORMAL", "BAD"): "Investigate model",
    ("NORMAL", "UNKNOWN"): "Continue monitoring",
    ("WARNING", "GOOD"): "Continue",
    ("WARNING", "BAD"): "Investigate model",
    ("WARNING", "UNKNOWN"): "Continue monitoring",
    ("SIGNIFICANT", "GOOD"): "Investigate",
    ("SIGNIFICANT", "BAD"): "Retrain / review",
    ("SIGNIFICANT", "UNKNOWN"): "Obtain ground truth",
}

#: Maps each of the 9 cell labels onto the PRD's RETAIN/EVALUATE/RETRAIN
#: vocabulary. "Obtain ground truth" maps to RETRAIN (not EVALUATE) because
#: that is what `should_retrain` actually fires on below -- the display text
#: undersells that the system proceeds to retrain in that cell. This mapping
#: was derived by checking consistency against `should_retrain` for all 9
#: (drift_level, evaluation_level) combinations; see EXP-06 evidence.
CELL_TO_STATE: dict[str, "TriggerState"] = {
    "Continue": "RETAIN",
    "Continue monitoring": "RETAIN",
    "Investigate model": "EVALUATE",
    "Investigate": "EVALUATE",
    "Retrain / review": "RETRAIN",
    "Obtain ground truth": "RETRAIN",
}

PREDICATE_TEXT = "Retrain = (DriftLevel == SIGNIFICANT) and (EvaluationLevel != GOOD)"


def joint_cell(drift_level: str, evaluation_level: str) -> str:
    """The human-readable Section 8.4 matrix cell for this (drift, incumbent) pair."""
    return CELL_TABLE.get((drift_level, evaluation_level), "unspecified")


def should_retrain(drift_level: str, evaluation_level: str) -> bool:
    """The exact `fire` boolean every call site trains a candidate on."""
    return drift_level == "SIGNIFICANT" and evaluation_level != "GOOD"


def decide_trigger_state(drift_level: str, evaluation_level: str) -> TriggerState:
    """RETAIN / EVALUATE / RETRAIN, derived from the real `joint_cell` matrix."""
    cell = joint_cell(drift_level, evaluation_level)
    return CELL_TO_STATE.get(cell, "EVALUATE")
