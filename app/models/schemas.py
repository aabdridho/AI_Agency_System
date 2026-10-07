from typing import Literal
from pydantic import BaseModel, Field

RequirementStatus = Literal[
    "CONFIRMED",
    "INFERRED",
    "PROPOSED",
    "UNKNOWN",
    "INTERNAL_DECISION"
]

class RequirementItem(BaseModel):
    key: str
    value: str | bool | int | float | list[str] | None = None
    status: RequirementStatus
    source: str
    blocking: bool = False
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

class DiscoveryResult(BaseModel):
    project_type: str
    confirmed: list[RequirementItem]
    inferred: list[RequirementItem]
    proposed: list[RequirementItem] = []
    unknown: list[RequirementItem]
    internal_decisions: list[RequirementItem]
    questions: list[str]
    ready_for_final_approval: bool
    client_approved: bool = False
    ready_for_development: bool
