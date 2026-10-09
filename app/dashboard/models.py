from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# One entry per folder in app/, in pipeline order.
STAGE_KEYS = (
    "discovery",
    "documentation",
    "routing",
    "execution",
    "delivery",
    "economics",
    "deployment",
)

StageStatus = Literal["todo", "wait", "done", "fail"]


class StageState(BaseModel):
    key: str
    status: StageStatus
    detail: str


class ProjectSummary(BaseModel):
    name: str
    has_workspace: bool
    stages: list[StageState]


class ProjectDetail(ProjectSummary):
    routing_source: Literal["saved", "preview"] | None = None
    routing: dict[str, Any] | None = None
    execution: dict[str, Any] | None = None
    execution_events: list[dict[str, Any]] | None = None
    usage_records: list[dict[str, Any]] | None = None
    delivery: dict[str, Any] | None = None
    deployment_plan: dict[str, Any] | None = None
    deployment_result: dict[str, Any] | None = None
    handoff: dict[str, Any] | None = None
    orchestration: dict[str, Any] | None = None


# ---------- GOAT tier config used by the dashboard ----------
TIER_ROLES = ("triage", "quick", "build", "deep", "create", "review", "esc")
KNOWN_MODELS = ("rules", "haiku", "sonnet", "opus", "fable", "luna", "sol", "astra")
Effort = Literal["low", "medium", "high", "xhigh"]
RoutingMode = Literal["auto", "manual"]


class Tier(BaseModel):
    model: str
    effort: Effort = "medium"

    @field_validator("model")
    @classmethod
    def _known(cls, v: str) -> str:
        if v not in KNOWN_MODELS:
            raise ValueError(f"unknown model '{v}'")
        return v


class TierConfig(BaseModel):
    mode: RoutingMode = "auto"
    tiers: dict[str, Tier] = Field(default_factory=dict)

    @field_validator("tiers")
    @classmethod
    def _roles(cls, v: dict[str, Tier]) -> dict[str, Tier]:
        unknown = set(v) - set(TIER_ROLES)
        if unknown:
            raise ValueError(f"unknown tier role(s): {', '.join(sorted(unknown))}")
        for role, tier in v.items():
            if role != "triage" and tier.model == "rules":
                raise ValueError(f"'{role}' needs a model; keyword rules only fit triage")
        return v
