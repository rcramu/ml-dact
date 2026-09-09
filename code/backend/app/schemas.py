"""Pydantic request models (response bodies are typed dicts — see routers)."""
from pydantic import BaseModel, Field


class TriggerTrainingRequest(BaseModel):
    trigger_type: str = Field(default="manual", description="drift | performance | schedule | data_availability | manual")
    scenario: str = Field(default="healthy", description="healthy | volume_anomaly | feature_drift | label_imbalance | regression")
    trigger_detail: str = Field(default="", description="Free-text reason, e.g. 'PSI=0.24 on customer_satisfaction'")


class RollbackRequest(BaseModel):
    reason: str = Field(default="manual rollback requested from UI")


class JointRetrainRequest(BaseModel):
    scenario: str = Field(default="feature_drift")
    seed: int = Field(default=42, ge=1, le=2_000_000_000)
    trigger_detail: str = Field(default="")


class ElectricityJointRetrainRequest(BaseModel):
    fold: int = Field(..., ge=0, le=4, description="Adjacent Elec2 transfer 0..4")
    trigger_detail: str = Field(default="", max_length=200)
