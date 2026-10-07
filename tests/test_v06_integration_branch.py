from app.execution.git_ops import GitOps
from app.execution.engine import ExecutionEngine
from app.routing.models import RoutingDecision, RoutingPlan

def test_integration_branch_name(tmp_path):
    git = GitOps(tmp_path)
    assert git.integration_branch("Data Eng Port") == "ai/integration/data-eng-port"

def test_qa_dry_run_targets_integration_branch(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "requirement.md").write_text("# Req", encoding="utf-8")

    plan = RoutingPlan(
        project_name="demo",
        source_task_file=str(docs / "task.md"),
        decisions=[
            RoutingDecision(
                task_id="TASK-001",
                task_text="Run deterministic validation/lint/tests",
                category="qa",
                primary_owner="deterministic_qa",
                fallback_owner="codex",
                confidence=0.98,
                reason="test",
                escalation_trigger="test",
                max_escalations=1,
            )
        ],
    )
    report = ExecutionEngine().execute(plan, tmp_path, dry_run=True)
    assert report.records[0].branch == "ai/integration/demo"

def test_required_binaries_derive_from_plan(tmp_path):
    plan = RoutingPlan(
        project_name="demo",
        source_task_file="task.md",
        decisions=[
            RoutingDecision(
                task_id="TASK-001",
                task_text="Implement hero",
                category="frontend",
                primary_owner="claude_code",
                fallback_owner="codex",
                confidence=0.97,
                reason="test",
                escalation_trigger="test",
                max_escalations=1,
            ),
            RoutingDecision(
                task_id="TASK-002",
                task_text="Submit form",
                category="backend",
                primary_owner="codex",
                fallback_owner="claude_code",
                confidence=0.97,
                reason="test",
                escalation_trigger="test",
                max_escalations=1,
            ),
        ],
    )
    assert ExecutionEngine().required_binaries(plan) == {"git", "claude", "codex"}
