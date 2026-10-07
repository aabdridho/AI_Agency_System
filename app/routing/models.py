from typing import Literal
from pydantic import BaseModel, Field

Owner = Literal[
    "claude_code",
    "codex",
    "deterministic_qa",
    "internal_decision",
]

class RoutingDecision(BaseModel):
    task_id: str
    task_text: str
    category: str
    primary_owner: Owner
    fallback_owner: Owner | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    escalation_trigger: str | None = None
    max_escalations: int = 1

class RoutingPlan(BaseModel):
    project_name: str
    source_task_file: str
    decisions: list[RoutingDecision]
    policy_version: str = "0.5"
