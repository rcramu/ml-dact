"""SQLAlchemy ORM models for the Continuous Training Pipeline (req.md Sec. 11, 17, 28, 39, 49)."""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class TrainedModel(Base):
    """A model *name* that gets continuously retrained (req.md Sec. 1)."""
    __tablename__ = "models"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    owner_team: Mapped[str] = mapped_column(String(120), default="ml-platform")
    task_type: Mapped[str] = mapped_column(String(40), default="classification")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    versions: Mapped[list["ModelVersion"]] = relationship(back_populates="model", cascade="all, delete-orphan")
    dataset_versions: Mapped[list["DatasetVersion"]] = relationship(back_populates="model", cascade="all, delete-orphan")
    runs: Mapped[list["PipelineRun"]] = relationship(back_populates="model", cascade="all, delete-orphan")


class DatasetVersion(Base):
    """Versioned, seeded training dataset (req.md Sec. 11-14)."""
    __tablename__ = "dataset_versions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    model_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("models.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    scenario: Mapped[str] = mapped_column(String(40), default="healthy")  # healthy/volume_anomaly/feature_drift/label_imbalance/regression
    source_type: Mapped[str] = mapped_column(String(20), default="synthetic")
    location: Mapped[str] = mapped_column(String(200), default="")
    rows: Mapped[int] = mapped_column(Integer, default=0)
    features: Mapped[int] = mapped_column(Integer, default=8)
    train_split: Mapped[float] = mapped_column(Float, default=0.70)
    val_split: Mapped[float] = mapped_column(Float, default=0.15)
    test_split: Mapped[float] = mapped_column(Float, default=0.15)
    seed: Mapped[int] = mapped_column(Integer, default=42)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    model: Mapped["TrainedModel"] = relationship(back_populates="dataset_versions")
    records: Mapped[list["RawRecord"]] = relationship(back_populates="dataset_version", cascade="all, delete-orphan")
    quality_checks: Mapped[list["DataQualityCheck"]] = relationship(back_populates="dataset_version", cascade="all, delete-orphan")


class RawRecord(Base):
    """One synthetic ingested tabular transaction row (req.md Sec. 12-14) — feeds PyTorch training."""
    __tablename__ = "raw_records"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    dataset_version_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("dataset_versions.id"), nullable=False)
    split: Mapped[str] = mapped_column(String(10), default="train")  # train/val/test
    monthly_charges: Mapped[float] = mapped_column(Float, default=0.0)
    support_tickets: Mapped[int] = mapped_column(Integer, default=12)
    customer_satisfaction: Mapped[float] = mapped_column(Float, default=0.0)
    tenure_days: Mapped[int] = mapped_column(Integer, default=365)
    service_count: Mapped[int] = mapped_column(Integer, default=1)
    is_month_to_month: Mapped[bool] = mapped_column(Boolean, default=False)
    usage_score: Mapped[float] = mapped_column(Float, default=0.5)
    late_payments: Mapped[int] = mapped_column(Integer, default=0)
    age: Mapped[int] = mapped_column(Integer, default=45)
    label: Mapped[int] = mapped_column(Integer, default=0)  # is_churn
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    dataset_version: Mapped["DatasetVersion"] = relationship(back_populates="records")


class DataQualityCheck(Base):
    """Pre-training data quality gate results (req.md Sec. 32)."""
    __tablename__ = "data_quality_checks"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    dataset_version_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("dataset_versions.id"), nullable=False)
    check_name: Mapped[str] = mapped_column(String(60), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, default=True)
    detail: Mapped[str] = mapped_column(Text, default="")

    dataset_version: Mapped["DatasetVersion"] = relationship(back_populates="quality_checks")


class ModelVersion(Base):
    """A trained candidate/champion/archived/rejected model version (req.md Sec. 18-19)."""
    __tablename__ = "model_versions"
    __table_args__ = (UniqueConstraint("model_id", "version", name="uq_model_version"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    model_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("models.id"), nullable=False)
    run_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("pipeline_runs.id"), nullable=True)
    dataset_version_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("dataset_versions.id"), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    stage: Mapped[str] = mapped_column(String(20), default="candidate")  # candidate/staging/production/archived/rejected/rolled_back
    framework: Mapped[str] = mapped_column(String(40), default="PyTorch")
    architecture: Mapped[str] = mapped_column(String(120), default="Feed-forward MLP (8-16-8-1)")
    hyperparams_json: Mapped[str] = mapped_column(Text, default="{}")
    mlflow_run_id: Mapped[str] = mapped_column(String(60), default="")
    registry_version: Mapped[int | None] = mapped_column(Integer, nullable=True)  # MLflow Model Registry's OWN version number (Sec. 18)
    git_commit: Mapped[str] = mapped_column(String(40), default="")
    train_f1: Mapped[float] = mapped_column(Float, default=0.0)
    val_f1: Mapped[float] = mapped_column(Float, default=0.0)
    test_f1: Mapped[float] = mapped_column(Float, default=0.0)
    accuracy: Mapped[float] = mapped_column(Float, default=0.0)
    precision: Mapped[float] = mapped_column(Float, default=0.0)
    recall: Mapped[float] = mapped_column(Float, default=0.0)
    roc_auc: Mapped[float] = mapped_column(Float, default=0.0)
    pr_auc: Mapped[float] = mapped_column(Float, default=0.0)
    is_champion: Mapped[bool] = mapped_column(Boolean, default=False)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    model: Mapped["TrainedModel"] = relationship(back_populates="versions")


class PipelineRun(Base):
    """One end-to-end retraining DAG execution (req.md Sec. 9-10, 53)."""
    __tablename__ = "pipeline_runs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    model_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("models.id"), nullable=False)
    dataset_version_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("dataset_versions.id"), nullable=True)
    trigger_type: Mapped[str] = mapped_column(String(20), default="manual")  # drift/performance/schedule/data_availability/volume_anomaly/manual
    trigger_detail: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(20), default="RUNNING")  # RUNNING/SUCCESS/REJECTED/BLOCKED/FAILED
    outcome: Mapped[str] = mapped_column(String(40), default="")  # e.g. MODEL_NOT_PROMOTED / DATA_VOLUME_ALERT
    candidate_version_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    model: Mapped["TrainedModel"] = relationship(back_populates="runs")
    stages: Mapped[list["PipelineStage"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class PipelineStage(Base):
    """One of the 16 DAG stages (req.md Sec. 10)."""
    __tablename__ = "pipeline_stages"
    __table_args__ = (UniqueConstraint("run_id", "stage_name", name="uq_run_stage"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("pipeline_runs.id"), nullable=False)
    stage_name: Mapped[str] = mapped_column(String(60), nullable=False)
    stage_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING/RUNNING/SUCCESS/FAILED/BLOCKED/SKIPPED
    detail_json: Mapped[str] = mapped_column(Text, default="{}")
    simulated_minutes: Mapped[float] = mapped_column(Float, default=0.0)  # req.md Sec. 29 SLA — simulated realistic duration
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    run: Mapped["PipelineRun"] = relationship(back_populates="stages")


class EvaluationResult(Base):
    """Champion-vs-challenger evaluation gate decision (req.md Sec. 20-23)."""
    __tablename__ = "evaluation_results"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("pipeline_runs.id"), nullable=False)
    candidate_version_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    champion_version_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    candidate_metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    champion_metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    regression_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    gate_result: Mapped[str] = mapped_column(String(10), default="PASS")  # PASS/FAIL
    reasons: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DeploymentEvent(Base):
    """Canary rollout progression / rollback (req.md Sec. 25-27)."""
    __tablename__ = "deployment_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    model_version_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("model_versions.id"), nullable=False)
    stage: Mapped[str] = mapped_column(String(20), nullable=False)  # stage/smoke_test/canary_5/canary_25/canary_50/canary_100/production/rolled_back
    status: Mapped[str] = mapped_column(String(20), default="SUCCESS")
    detail: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RollbackEvent(Base):
    """Automatic/manual rollback record (req.md Sec. 26-27)."""
    __tablename__ = "rollback_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    model_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("models.id"), nullable=False)
    from_version_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    to_version_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    reason: Mapped[str] = mapped_column(String(200), default="")
    triggered_by: Mapped[str] = mapped_column(String(20), default="automatic")  # automatic/manual
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Alert(Base):
    """Slack / PagerDuty style alert (req.md Sec. 37-38)."""
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    run_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("pipeline_runs.id"), nullable=True)
    model_version_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    category: Mapped[str] = mapped_column(String(40), default="training_started")
    severity: Mapped[str] = mapped_column(String(20), default="INFO")  # INFO/WARNING/CRITICAL
    channel: Mapped[str] = mapped_column(String(20), default="slack")  # slack/pagerduty
    message: Mapped[str] = mapped_column(Text, default="")
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SlaConfig(Base):
    """Per-stage SLA thresholds (req.md Sec. 28-29)."""
    __tablename__ = "sla_configs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    stage_name: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    max_minutes: Mapped[float] = mapped_column(Float, default=10.0)


class SlaViolation(Base):
    """A stage that exceeded its configured SLA (req.md Sec. 28-29)."""
    __tablename__ = "sla_violations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("pipeline_runs.id"), nullable=False)
    stage_name: Mapped[str] = mapped_column(String(60), nullable=False)
    actual_minutes: Mapped[float] = mapped_column(Float, default=0.0)
    max_minutes: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    """Governance / audit trail — who/what/when/why (req.md Sec. 48)."""
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    actor: Mapped[str] = mapped_column(String(60), default="continuous-training-pipeline")
    action: Mapped[str] = mapped_column(String(40), nullable=False)  # promote/reject/rollback/trigger
    resource_type: Mapped[str] = mapped_column(String(40), default="model_version")
    resource_id: Mapped[str] = mapped_column(String(60), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
