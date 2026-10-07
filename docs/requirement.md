# V0.6 System Requirement

## Goal
Execute routed project tasks through local Claude Code / Codex CLI while preserving auditability and repository isolation.

## Required rules
- Default mode is dry-run.
- Real execution requires explicit confirmation.
- One task uses one primary owner.
- One branch per task.
- No direct automatic push to main.
- Fallback may occur only after primary failure.
- Maximum fallback/escalation is one.
- Deterministic QA executes before AI diagnosis where routing policy requires it.
- Operational execution data stays outside the client/project repository.
- Project docs remain the implementation source of truth.
