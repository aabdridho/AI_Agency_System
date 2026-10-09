from typing import Literal
from pydantic import BaseModel, Field

ExecutionStatus = Literal[
    "pending",
    "dry_run",
    "running",
    "success",
    "failed",
    "skipped",
]

class ExecutionRecord(BaseModel):
    task_id: str
    owner: str
    branch: str
    status: ExecutionStatus
    command_preview: str | None = None
    return_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    escalated: bool = False
    escalation_owner: str | None = None

    # QA auto-repair audit metadata.
    initial_qa_failed: bool = False
    repair_attempted: bool = False
    repair_attempts: int = 0
    repair_owner: str | None = None
    repair_branch: str | None = None
    repair_succeeded: bool = False
    qa_profile: str | None = None

class ExecutionReport(BaseModel):
    project_name: str
    dry_run: bool
    records: list[ExecutionRecord]

    # Latest execution identity. None keeps legacy reports valid.
    run_id: str | None = None

    policy_version: str = "0.6"
