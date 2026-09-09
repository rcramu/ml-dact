"""Dict serializers shared by every router (keeps response shapes consistent)."""
import json

from . import models as m


def model_dict(model: m.TrainedModel) -> dict:
    return {
        "id": model.id, "name": model.name, "description": model.description,
        "owner_team": model.owner_team, "task_type": model.task_type,
        "created_at": model.created_at.isoformat(),
    }


def dataset_version_dict(d: m.DatasetVersion) -> dict:
    return {
        "id": d.id, "model_id": d.model_id, "name": d.name, "version": d.version,
        "scenario": d.scenario, "source_type": d.source_type, "location": d.location,
        "rows": d.rows, "features": d.features, "train_split": d.train_split,
        "val_split": d.val_split, "test_split": d.test_split, "seed": d.seed,
        "created_at": d.created_at.isoformat(),
    }


def raw_record_dict(r: m.RawRecord) -> dict:
    return {
        "id": r.id, "dataset_version_id": r.dataset_version_id, "split": r.split,
        "monthly_charges": r.monthly_charges, "support_tickets": r.support_tickets, "customer_satisfaction": r.customer_satisfaction,
        "tenure_days": r.tenure_days, "service_count": r.service_count,
        "is_month_to_month": r.is_month_to_month, "usage_score": r.usage_score,
        "late_payments": r.late_payments, "age": r.age, "label": r.label,
        "created_at": r.created_at.isoformat(),
    }


def data_quality_check_dict(c: m.DataQualityCheck) -> dict:
    return {
        "id": c.id, "dataset_version_id": c.dataset_version_id, "check_name": c.check_name,
        "passed": c.passed, "detail": c.detail,
    }


def model_version_dict(v: m.ModelVersion) -> dict:
    return {
        "id": v.id, "model_id": v.model_id, "run_id": v.run_id, "dataset_version_id": v.dataset_version_id,
        "version": v.version, "stage": v.stage, "framework": v.framework, "architecture": v.architecture,
        "hyperparams": json.loads(v.hyperparams_json or "{}"), "mlflow_run_id": v.mlflow_run_id,
        "registry_version": v.registry_version, "git_commit": v.git_commit, "train_f1": v.train_f1, "val_f1": v.val_f1, "test_f1": v.test_f1,
        "accuracy": v.accuracy, "precision": v.precision, "recall": v.recall, "roc_auc": v.roc_auc,
        "pr_auc": v.pr_auc, "is_champion": v.is_champion,
        "promoted_at": v.promoted_at.isoformat() if v.promoted_at else None,
        "created_at": v.created_at.isoformat(),
    }


def pipeline_stage_dict(s: m.PipelineStage) -> dict:
    return {
        "id": s.id, "run_id": s.run_id, "stage_name": s.stage_name, "stage_order": s.stage_order,
        "status": s.status, "detail": json.loads(s.detail_json or "{}"), "simulated_minutes": s.simulated_minutes,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "completed_at": s.completed_at.isoformat() if s.completed_at else None,
    }


def pipeline_run_dict(run: m.PipelineRun, include_stages: bool = False) -> dict:
    d = {
        "id": run.id, "model_id": run.model_id, "dataset_version_id": run.dataset_version_id,
        "trigger_type": run.trigger_type, "trigger_detail": run.trigger_detail, "status": run.status,
        "outcome": run.outcome, "candidate_version_id": run.candidate_version_id,
        "started_at": run.started_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }
    if include_stages:
        d["stages"] = [pipeline_stage_dict(s) for s in sorted(run.stages, key=lambda s: s.stage_order)]
    return d


def evaluation_result_dict(e: m.EvaluationResult) -> dict:
    return {
        "id": e.id, "run_id": e.run_id, "candidate_version_id": e.candidate_version_id,
        "champion_version_id": e.champion_version_id,
        "candidate_metrics": json.loads(e.candidate_metrics_json or "{}"),
        "champion_metrics": json.loads(e.champion_metrics_json or "{}"),
        "regression_pct": e.regression_pct, "gate_result": e.gate_result, "reasons": e.reasons,
        "created_at": e.created_at.isoformat(),
    }


def deployment_event_dict(e: m.DeploymentEvent) -> dict:
    return {
        "id": e.id, "model_version_id": e.model_version_id, "stage": e.stage,
        "status": e.status, "detail": e.detail, "created_at": e.created_at.isoformat(),
    }


def rollback_event_dict(e: m.RollbackEvent) -> dict:
    return {
        "id": e.id, "model_id": e.model_id, "from_version_id": e.from_version_id,
        "to_version_id": e.to_version_id, "reason": e.reason, "triggered_by": e.triggered_by,
        "created_at": e.created_at.isoformat(),
    }


def alert_dict(a: m.Alert) -> dict:
    return {
        "id": a.id, "run_id": a.run_id, "model_version_id": a.model_version_id, "category": a.category,
        "severity": a.severity, "channel": a.channel, "message": a.message, "resolved": a.resolved,
        "created_at": a.created_at.isoformat(),
        "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
    }


def sla_violation_dict(v: m.SlaViolation) -> dict:
    return {
        "id": v.id, "run_id": v.run_id, "stage_name": v.stage_name,
        "actual_minutes": v.actual_minutes, "max_minutes": v.max_minutes,
        "created_at": v.created_at.isoformat(),
    }


def audit_log_dict(a: m.AuditLog) -> dict:
    return {
        "id": a.id, "actor": a.actor, "action": a.action, "resource_type": a.resource_type,
        "resource_id": a.resource_id, "detail": a.detail, "created_at": a.created_at.isoformat(),
    }
