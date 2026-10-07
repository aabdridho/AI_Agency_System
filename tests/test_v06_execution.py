from pathlib import Path

from app.execution.git_ops import GitOps
from app.execution.prompt_builder import TaskPromptBuilder
from app.execution.engine import ExecutionEngine
from app.routing.models import RoutingDecision, RoutingPlan


def test_branch_name_isolated(tmp_path):
    git = GitOps(tmp_path)
    branch = git.sanitize_branch("TASK-003", "Implement Hero Section")
    assert branch.startswith("ai/task-003-")
    assert "hero-section" in branch


def test_prompt_uses_project_docs(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "requirement.md").write_text("# Req\nDark theme", encoding="utf-8")
    prompt = TaskPromptBuilder().build(tmp_path, "Implement hero")
    assert "Dark theme" in prompt
    assert "Implement hero" in prompt


def test_dry_run_does_not_require_cli(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "requirement.md").write_text("# Req", encoding="utf-8")

    plan = RoutingPlan(
        project_name="p",
        source_task_file=str(docs / "task.md"),
        decisions=[
            RoutingDecision(
                task_id="TASK-001",
                task_text="Implement hero section",
                category="frontend",
                primary_owner="claude_code",
                fallback_owner="codex",
                confidence=0.97,
                reason="test",
                escalation_trigger="test",
                max_escalations=1,
            )
        ],
    )

    report = ExecutionEngine().execute(plan, tmp_path, dry_run=True)
    assert report.records[0].status == "dry_run"
    assert report.records[0].owner == "claude_code"


def test_dry_run_preserves_one_primary_owner(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "requirement.md").write_text("# Req", encoding="utf-8")

    plan = RoutingPlan(
        project_name="p",
        source_task_file=str(docs / "task.md"),
        decisions=[
            RoutingDecision(
                task_id="TASK-001",
                task_text="Submit form data to email",
                category="backend",
                primary_owner="codex",
                fallback_owner="claude_code",
                confidence=0.97,
                reason="test",
                escalation_trigger="test",
                max_escalations=1,
            )
        ],
    )

    report = ExecutionEngine().execute(plan, tmp_path, dry_run=True)
    rec = report.records[0]
    assert rec.owner == "codex"
    assert rec.escalated is False
