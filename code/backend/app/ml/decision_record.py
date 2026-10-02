"""EXP-07 decision-lineage replay: reconstruct a persisted decision record and
replay it through the real policy/gate functions to check it reproduces the
recorded action.

Two kinds of persisted decision exist in this codebase:
  - JointDecision: the Section 8.4 trigger decision (RETAIN/EVALUATE/RETRAIN),
    persisted by routers/joint.py and routers/electricity.py.
  - EvaluationResult: the PROMOTE/REJECT gate decision, persisted by
    pipeline_engine.run_pipeline and routers/electricity.py.
Rollback (RollbackEvent) is a manually/externally triggered action in this
codebase today (see EXP-07 evidence) -- its *mechanics* are deterministic and
covered by EXP-06, but there is no automated "should we roll back" policy to
replay here, so it is out of scope for this replay.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from .. import models as m
from . import policy
from .gates import evaluation_gate


def replay_joint_decision(row: m.JointDecision) -> dict:
    replayed_state = policy.decide_trigger_state(row.drift_level, row.evaluation_level)
    replayed_trained = policy.should_retrain(row.drift_level, row.evaluation_level)
    return {
        "decision_id": row.id,
        "kind": "joint_decision",
        "scenario_key": row.scenario_key,
        "recorded_state": row.decided_state,
        "replayed_state": replayed_state,
        "recorded_trained": row.trained,
        "replayed_trained": replayed_trained,
        "match": (replayed_state == row.decided_state) and (replayed_trained == row.trained),
        "policy_version": row.policy_version,
        "threshold_config_version": row.threshold_config_version,
    }


def replay_evaluation_result(row: m.EvaluationResult) -> dict:
    candidate_metrics = json.loads(row.candidate_metrics_json or "{}")
    champion_metrics_raw = json.loads(row.champion_metrics_json or "{}")
    champion_metrics = champion_metrics_raw or None
    replayed_result, replayed_regression_pct, replayed_reasons = evaluation_gate(candidate_metrics, champion_metrics)
    return {
        "decision_id": row.id,
        "kind": "evaluation_result",
        "run_id": row.run_id,
        "recorded_gate_result": row.gate_result,
        "replayed_gate_result": replayed_result,
        "recorded_regression_pct": row.regression_pct,
        "replayed_regression_pct": replayed_regression_pct,
        "match": replayed_result == row.gate_result,
        "policy_version": row.policy_version,
        "threshold_config_version": row.threshold_config_version,
    }


def replay_all(db: Session) -> dict:
    joint_rows = db.query(m.JointDecision).order_by(m.JointDecision.created_at.asc()).all()
    eval_rows = db.query(m.EvaluationResult).order_by(m.EvaluationResult.created_at.asc()).all()
    joint_results = [replay_joint_decision(r) for r in joint_rows]
    eval_results = [replay_evaluation_result(r) for r in eval_rows]
    all_results = joint_results + eval_results
    matched = sum(1 for r in all_results if r["match"])
    return {
        "total_decisions_replayed": len(all_results),
        "matched": matched,
        "mismatched": len(all_results) - matched,
        "joint_decisions": joint_results,
        "evaluation_results": eval_results,
    }
