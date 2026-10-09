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

    # GOAT capability route chosen before provider/model resolution.
    goat_tier: str = "build"

    # V0.16 observable triage contract.
    route: str = "build"
    risk: Literal["low", "medium", "high"] = "medium"
    checks: list[str] = Field(default_factory=list)
    triage_mode: Literal["rules", "model"] = "rules"
    verifier: str = "deterministic_qa"

    primary_owner: Owner
    fallback_owner: Owner | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str

    # V0.13 explicit model attribution.
    # Model selection is part of the routing contract so billing never
    # depends on an invisible provider default.
    primary_model: str | None = None
    fallback_model: str | None = None
    primary_effort: str | None = None
    fallback_effort: str | None = None
    model_source: str = "routing_policy"

    escalation_trigger: str | None = None
    max_escalations: int = 1

class RoutingPlan(BaseModel):
    project_name: str
    source_task_file: str
    decisions: list[RoutingDecision]
    policy_version: str = "0.13"
