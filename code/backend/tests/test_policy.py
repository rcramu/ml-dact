"""EXP-06 — MEDP policy-state test suite (JSS PRD Section 8).

Every test below calls the real production functions directly:
- app.ml.policy.decide_trigger_state / should_retrain / joint_cell
  (extracted from backend/app/routers/joint.py during this evidence program;
  verified behavior-preserving against the pre-refactor stored output in
  k8s/metrics/electricity-natural.json)
- app.ml.gates.evaluation_gate
- app.pipeline_engine.rollback (against an isolated in-memory DB, see conftest.py)

No policy logic is reimplemented here -- a change to production behavior
should break these tests, not just a reimplementation of it.
"""
from datetime import datetime, timedelta

import pytest

from app.ml import policy
from app.ml.gates import evaluation_gate
from app import pipeline_engine as pe
from app import models as m


# ---------------------------------------------------------------------------
# PRD Section 8 trigger-state table
# ---------------------------------------------------------------------------

TRIGGER_STATE_TABLE = [
    # (drift_level, evaluation_level, expected_state, PRD row)
    ("NORMAL", "GOOD", "RETAIN", "stable distribution + healthy incumbent"),
    ("SIGNIFICANT", "GOOD", "EVALUATE", "drift + healthy incumbent"),
    ("SIGNIFICANT", "BAD", "RETRAIN", "drift + degraded incumbent"),
    # Additional real states the production matrix distinguishes that the
    # PRD's 3-row table does not enumerate -- reported, not invented:
    ("WARNING", "GOOD", "RETAIN", "warning drift + healthy incumbent (treated as stable)"),
    ("WARNING", "BAD", "EVALUATE", "warning drift + degraded incumbent (not yet significant)"),
    ("NORMAL", "BAD", "EVALUATE", "no drift but degraded incumbent (performance-only signal)"),
    ("NORMAL", "UNKNOWN", "RETAIN", "no drift, champion health unscored"),
    ("WARNING", "UNKNOWN", "RETAIN", "warning drift, champion health unscored"),
    ("SIGNIFICANT", "UNKNOWN", "RETRAIN", "drift present, champion health unscored (fires despite 'Obtain ground truth' label)"),
]


@pytest.mark.parametrize("drift,ev,expected,desc", TRIGGER_STATE_TABLE)
def test_trigger_state_table(drift, ev, expected, desc):
    assert policy.decide_trigger_state(drift, ev) == expected, desc


def test_should_retrain_matches_trigger_state_retrain():
    """should_retrain (the actual boolean every call site trains on) must be
    exactly equivalent to decide_trigger_state == RETRAIN, for all 9 cells."""
    for drift in ("NORMAL", "WARNING", "SIGNIFICANT"):
        for ev in ("GOOD", "BAD", "UNKNOWN"):
            expected_retrain = policy.decide_trigger_state(drift, ev) == "RETRAIN"
            assert policy.should_retrain(drift, ev) == expected_retrain, (drift, ev)


def test_unspecified_combination_falls_back_to_evaluate():
    assert policy.joint_cell("NOT_A_LEVEL", "GOOD") == "unspecified"
    assert policy.decide_trigger_state("NOT_A_LEVEL", "GOOD") == "EVALUATE"


# ---------------------------------------------------------------------------
# Candidate gate: REJECT / PROMOTE (evaluation_gate)
# ---------------------------------------------------------------------------

def test_candidate_below_quality_floor_is_rejected():
    candidate = {"f1": 0.65, "precision": 0.65, "recall": 0.65}
    result, regression_pct, reasons = evaluation_gate(candidate, None)
    assert result == "FAIL"
    assert "below minimum" in reasons


def test_candidate_violates_recall_constraint_vs_champion_is_rejected():
    """Candidate clears its own floors but loses recall ground against champion."""
    candidate = {"f1": 0.75, "precision": 0.70, "recall": 0.62}
    champion = {"f1": 0.75, "precision": 0.70, "recall": 0.80}
    result, regression_pct, reasons = evaluation_gate(candidate, champion)
    assert result == "FAIL"
    assert "below champion recall" in reasons


def test_candidate_passing_all_constraints_is_promoted():
    candidate = {"f1": 0.80, "precision": 0.78, "recall": 0.75}
    champion = {"f1": 0.75, "precision": 0.72, "recall": 0.70}
    result, regression_pct, reasons = evaluation_gate(candidate, champion)
    assert result == "PASS"
    assert regression_pct is not None and regression_pct < 0  # candidate improved on champion


def test_regression_beyond_budget_is_rejected():
    candidate = {"f1": 0.60, "precision": 0.70, "recall": 0.70}  # >10% F1 regression vs champion
    champion = {"f1": 0.75, "precision": 0.70, "recall": 0.65}
    result, regression_pct, reasons = evaluation_gate(candidate, champion)
    assert result == "FAIL"
    assert regression_pct == pytest.approx(20.0, abs=0.01)
    assert "exceeds max allowed" in reasons


# ---------------------------------------------------------------------------
# Boundary / epsilon
# ---------------------------------------------------------------------------

def test_f1_floor_boundary_is_inclusive():
    candidate = {"f1": 0.70, "precision": 0.70, "recall": 0.70}  # exactly at the floor
    result, _, _ = evaluation_gate(candidate, None)
    assert result == "PASS"


def test_f1_floor_minus_epsilon_fails():
    candidate = {"f1": 0.70 - 1e-9, "precision": 0.70, "recall": 0.70}
    result, _, _ = evaluation_gate(candidate, None)
    assert result == "FAIL"


def test_f1_floor_plus_epsilon_passes():
    candidate = {"f1": 0.70 + 1e-9, "precision": 0.70, "recall": 0.70}
    result, _, _ = evaluation_gate(candidate, None)
    assert result == "PASS"


def test_regression_budget_boundary_is_inclusive():
    """regression_pct > max_regression_pct fails; == max_regression_pct passes."""
    champion = {"f1": 1.00, "precision": 0.80, "recall": 0.80}
    candidate_at_budget = {"f1": 0.90, "precision": 0.80, "recall": 0.80}  # exactly 10% regression
    result, regression_pct, _ = evaluation_gate(candidate_at_budget, champion)
    assert regression_pct == pytest.approx(10.0)
    assert result == "PASS"


# ---------------------------------------------------------------------------
# Missing metric / stale champion / determinism
# ---------------------------------------------------------------------------

def test_missing_metric_raises_keyerror():
    """evaluation_gate does not currently guard against a missing metric key --
    this test documents the real (unguarded) behavior rather than inventing a
    graceful fallback that doesn't exist in production."""
    candidate = {"f1": 0.80, "precision": 0.80}  # recall missing
    with pytest.raises(KeyError):
        evaluation_gate(candidate, None)


def test_stale_champion_with_zero_f1_skips_regression_check():
    """A champion dict with f1<=0 (e.g. a placeholder/never-scored champion)
    is treated as 'no champion' for the regression check (champion.get('f1',0) > 0)."""
    candidate = {"f1": 0.72, "precision": 0.65, "recall": 0.65}
    stale_champion = {"f1": 0.0, "precision": 0.0, "recall": 0.0}
    result, regression_pct, reasons = evaluation_gate(candidate, stale_champion)
    assert regression_pct is None
    assert result == "PASS"


def test_duplicate_candidate_yields_identical_decision():
    """Two distinct candidate dicts with identical metrics must produce an
    identical gate decision -- the gate is pure, not keyed by identity."""
    champion = {"f1": 0.75, "precision": 0.70, "recall": 0.70}
    candidate_a = {"f1": 0.72, "precision": 0.65, "recall": 0.65}
    candidate_b = dict(candidate_a)  # separate object, same values
    assert candidate_a is not candidate_b
    assert evaluation_gate(candidate_a, champion) == evaluation_gate(candidate_b, champion)


def test_repeated_candidate_submission_is_idempotent():
    """Re-submitting the same candidate dict for evaluation multiple times
    must not accumulate state or change the outcome."""
    candidate = {"f1": 0.72, "precision": 0.65, "recall": 0.65}
    champion = {"f1": 0.75, "precision": 0.70, "recall": 0.70}
    first = evaluation_gate(candidate, champion)
    for _ in range(5):
        assert evaluation_gate(candidate, champion) == first


# ---------------------------------------------------------------------------
# ROLLBACK (integration-level: real pipeline_engine.rollback against an
# isolated in-memory DB -- no live Postgres/MLflow required)
# ---------------------------------------------------------------------------

def _make_model_with_two_versions(db_session):
    model = m.TrainedModel(name="test-model")
    db_session.add(model)
    db_session.flush()

    v1 = m.ModelVersion(model_id=model.id, version=1, stage="rolled_back_source_archived", is_champion=False, test_f1=0.75)
    v1.stage = "archived"
    v2 = m.ModelVersion(model_id=model.id, version=2, stage="production", is_champion=True, test_f1=0.55)
    db_session.add_all([v1, v2])
    db_session.flush()
    db_session.commit()
    return model, v1, v2


def test_failed_promoted_candidate_triggers_rollback(db_session, monkeypatch):
    """Failed promoted candidate -> ROLLBACK: v2 was promoted, later found
    degraded in production, and must be rolled back to v1."""
    monkeypatch.setattr(pe.mlflow_utils, "transition_stage", lambda *a, **k: None)
    model, v1, v2 = _make_model_with_two_versions(db_session)

    event = pe.rollback(db_session, model, reason="production F1 regression detected", triggered_by="automatic")

    db_session.refresh(v1)
    db_session.refresh(v2)
    assert v2.is_champion is False and v2.stage == "rolled_back"
    assert v1.is_champion is True and v1.stage == "production"
    assert event.from_version_id == v2.id
    assert event.to_version_id == v1.id


def test_rollback_after_promotion_requires_an_archived_predecessor(db_session, monkeypatch):
    """Rollback after promotion with no prior archived version is a hard
    failure, not a silent no-op -- there is nothing to roll back to."""
    monkeypatch.setattr(pe.mlflow_utils, "transition_stage", lambda *a, **k: None)
    model = m.TrainedModel(name="test-model-no-history")
    db_session.add(model)
    db_session.flush()
    v1 = m.ModelVersion(model_id=model.id, version=1, stage="production", is_champion=True, test_f1=0.80)
    db_session.add(v1)
    db_session.flush()
    db_session.commit()

    with pytest.raises(ValueError, match="no previous archived version"):
        pe.rollback(db_session, model, reason="test", triggered_by="automatic")


def test_rollback_with_no_current_champion_fails_closed(db_session, monkeypatch):
    monkeypatch.setattr(pe.mlflow_utils, "transition_stage", lambda *a, **k: None)
    model = m.TrainedModel(name="test-model-no-champion")
    db_session.add(model)
    db_session.flush()
    db_session.commit()

    with pytest.raises(ValueError, match="no current production version"):
        pe.rollback(db_session, model, reason="test", triggered_by="automatic")
