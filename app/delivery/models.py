from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field

ReadinessStatus = Literal["pass", "warning", "blocker"]
BlockerClass = Literal[
    "AUTO_RESOLVABLE_INTERNAL",
    "CLIENT_INPUT_REQUIRED",
    "HARD_TECHNICAL_BLOCKER",
]


class ReadinessCheck(BaseModel):
    check_id: str
    title: str
    status: ReadinessStatus
    detail: str
    remediation: str | None = None
    blocker_class: BlockerClass | None = None
    auto_resolvable: bool = False
    proposed_resolution: str | None = None


class ClientInputItem(BaseModel):
    section: str
    source_file: str | None = None
    fields: list[str] = Field(default_factory=list)
    note: str | None = None


class DeliveryReport(BaseModel):
    project_name: str
    project_root: str
    overall_status: Literal["ready", "warning", "blocked"]
    checks: list[ReadinessCheck] = Field(default_factory=list)
    production_commands: list[str] = Field(default_factory=list)
    source_execution_report: str | None = None
    blocker_summary: dict[str, int] = Field(default_factory=dict)
    client_input_request: str | None = None

    @property
    def blockers(self):
        return [c for c in self.checks if c.status == "blocker"]

    @property
    def warnings(self):
        return [c for c in self.checks if c.status == "warning"]
