from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


OrchestrationStatus = Literal[
    "idle",
    "running",
    "waiting_input",
    "waiting_approval",
    "failed",
    "completed",
]


class OrchestrationState(BaseModel):
    project_name: str

    status: OrchestrationStatus = "idle"

    current_stage: str | None = None

    completed_stages: list[str] = Field(
        default_factory=list
    )

    waiting_for: str | None = None

    failed_stage: str | None = None

    last_error: str | None = None

    updated_at: str | None = None
