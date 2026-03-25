from __future__ import annotations

from pydantic import BaseModel, Field


class CreateCaseRequest(BaseModel):
    profile: str = ""


class FactFeedbackRequest(BaseModel):
    type: str = "GENERAL"
    feedback_type: str | None = None
    comment: str | None = None
    model_config = {"extra": "allow"}


class SandboxInterventionNode(BaseModel):
    node_id: str
    new_val: float


class SandboxInterveneRequest(BaseModel):
    interventions: list[SandboxInterventionNode] = Field(default_factory=list)
    text: str = ""


class WorldlineInterveneRequest(BaseModel):
    text: str = ""


class CaseFeedbackRequest(BaseModel):
    feedback_type: str = "GENERAL"
    payload: dict = Field(default_factory=dict)
    
    model_config = {"extra": "allow"}
