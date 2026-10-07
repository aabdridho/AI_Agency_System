from pathlib import Path
from app.execution.qa import DeterministicQA
from app.execution.engine import ExecutionEngine
from app.routing.models import RoutingDecision, RoutingPlan


def test_no_qa_command_is_not_success(tmp_path):
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

    report = ExecutionEngine().execute(plan, tmp_path, dry_run=False)
    rec = report.records[0]
    assert rec.status == "failed"
    assert rec.return_code == 2
    assert "No executable deterministic QA command" in rec.stderr


def test_node_build_is_detected(tmp_path, monkeypatch):
    (tmp_path / "package.json").write_text(
        '{"scripts":{"build":"vite build"}}',
        encoding="utf-8",
    )
    monkeypatch.setattr("shutil.which", lambda name: "fake" if name in {"npm", "python"} else None)
    commands = DeterministicQA().detect_commands(tmp_path)
    assert ["npm", "run", "build"] in commands
