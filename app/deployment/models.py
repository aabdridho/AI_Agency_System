from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field

DeploymentMode = Literal["dry-run", "execute"]
DeploymentStatus = Literal["planned", "blocked", "ready", "deployed", "failed"]

class DeploymentCommand(BaseModel):
    label: str
    command: list[str]
    destructive_or_remote: bool = False

class DeploymentPlan(BaseModel):
    project_name: str
    project_root: str
    provider: str
    mode: DeploymentMode
    status: DeploymentStatus
    source_branch: str | None = None
    commit_sha: str | None = None
    commands: list[DeploymentCommand] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

class DeploymentResult(BaseModel):
    status: DeploymentStatus
    executed_commands: list[str] = Field(default_factory=list)
    output_tail: str | None = None
    deployment_url: str | None = None

class HandoffReport(BaseModel):
    project_name: str
    project_root: str
    provider: str
    source_branch: str | None = None
    commit_sha: str | None = None
    delivery_status: str | None = None
    deployment_status: str | None = None
    deployment_url: str | None = None
    environment_variables: list[str] = Field(default_factory=list)
    validation_commands: list[str] = Field(default_factory=list)
    remaining_client_inputs: list[str] = Field(default_factory=list)
    files: list[str] = Field(default_factory=list)
