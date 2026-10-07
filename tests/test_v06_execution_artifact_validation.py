from pathlib import Path
from types import SimpleNamespace

from app.execution.engine import ExecutionEngine
from app.execution.git_ops import GitOps
from app.routing.models import RoutingDecision, RoutingPlan


class NoChangeAdapter:
    binary = "fake"

    def available(self):
        return True

    def build_command(self, prompt):
        return ["fake", prompt]

    def run(self, repo, prompt, timeout=1800, stream=True):
        return SimpleNamespace(returncode=0, stdout="Done", stderr="")


class WriteFileAdapter(NoChangeAdapter):
    def run(self, repo, prompt, timeout=1800, stream=True):
        Path(repo, "implemented.txt").write_text("real artifact", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="Implemented", stderr="")


def _plan():
    return RoutingPlan(
        project_name="demo",
        source_task_file="docs/task.md",
        decisions=[
            RoutingDecision(
                task_id="TASK-001",
                task_text="Implement project scaffold",
                category="setup",
                primary_owner="codex",
                fallback_owner=None,
                confidence=1.0,
                reason="test",
                escalation_trigger="failure",
                max_escalations=0,
            )
        ],
    )


def _repo(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "requirement.md").write_text("# Requirement", encoding="utf-8")
    (docs / "task.md").write_text("# Tasks", encoding="utf-8")
    return tmp_path


def test_zero_exit_without_changes_is_failed(tmp_path):
    root = _repo(tmp_path)
    engine = ExecutionEngine()
    engine.adapters["codex"] = NoChangeAdapter()

    report = engine.execute(_plan(), root, dry_run=False)
    rec = report.records[0]

    assert rec.status == "failed"
    assert rec.return_code == 6
    assert "produced no repository changes" in rec.stderr

    git = GitOps(root)
    integration_sha = git.ref_sha("ai/integration/demo")
    assert git.ref_sha("ai/task-001-implement-project-scaffold") == integration_sha


def test_real_file_change_is_committed_and_merged(tmp_path):
    root = _repo(tmp_path)
    engine = ExecutionEngine()
    engine.adapters["codex"] = WriteFileAdapter()

    report = engine.execute(_plan(), root, dry_run=False)
    rec = report.records[0]

    assert rec.status == "success"
    assert (root / "implemented.txt").exists()

    git = GitOps(root)
    assert git.is_ancestor("ai/task-001-implement-project-scaffold", "ai/integration/demo")
    assert len(git.ref_sha("ai/integration/demo")) == 40
