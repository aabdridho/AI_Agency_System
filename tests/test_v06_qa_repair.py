
from pathlib import Path
from types import SimpleNamespace

from app.execution.engine import ExecutionEngine
from app.execution.git_ops import GitOps
from app.routing.models import RoutingDecision, RoutingPlan


class RepairAdapter:
    binary = "fake"

    def available(self):
        return True

    def build_command(self, prompt):
        return ["fake", prompt]

    def run(self, repo, prompt, timeout=1800, stream=True):
        Path(repo, "repair.txt").write_text("fixed", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="repair applied", stderr="")


class SequencedQA:
    def __init__(self):
        self.calls = 0

    def run(self, repo):
        self.calls += 1
        if self.calls == 1:
            return [
                (
                    ["npm.cmd", "run", "typecheck"],
                    SimpleNamespace(returncode=1, stdout="", stderr="TS2339 type error"),
                )
            ]
        return [
            (
                ["npm.cmd", "run", "typecheck"],
                SimpleNamespace(returncode=0, stdout="typecheck passed", stderr=""),
            )
        ]


def _plan():
    return RoutingPlan(
        project_name="demo",
        source_task_file="docs/task.md",
        decisions=[
            RoutingDecision(
                task_id="TASK-017",
                task_text="Validate submission flow end-to-end",
                category="qa",
                primary_owner="deterministic_qa",
                fallback_owner="codex",
                confidence=1.0,
                reason="test",
                escalation_trigger="qa failure",
                max_escalations=1,
            )
        ],
    )


def test_failed_qa_is_repaired_and_rerun(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "requirement.md").write_text("# Requirement", encoding="utf-8")
    (docs / "task.md").write_text("# Tasks", encoding="utf-8")

    engine = ExecutionEngine()
    engine.qa = SequencedQA()
    engine.adapters["codex"] = RepairAdapter()
    engine.adapters["claude_code"] = RepairAdapter()

    report = engine.execute(_plan(), tmp_path, dry_run=False)
    rec = report.records[0]

    assert rec.status == "success"
    assert rec.initial_qa_failed is True
    assert rec.repair_attempted is True
    assert rec.repair_succeeded is True
    assert rec.repair_owner == "codex"
    assert rec.repair_branch.startswith("ai/repair/task-017-attempt-")
    assert engine.qa.calls == 2

    git = GitOps(tmp_path)
    assert git.is_ancestor(rec.repair_branch, "ai/integration/demo")
    assert (tmp_path / "repair.txt").exists()


def test_qa_repair_can_be_disabled(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "requirement.md").write_text("# Requirement", encoding="utf-8")
    (docs / "task.md").write_text("# Tasks", encoding="utf-8")

    engine = ExecutionEngine()
    engine.qa = SequencedQA()
    engine.adapters["codex"] = RepairAdapter()

    report = engine.execute(
        _plan(),
        tmp_path,
        dry_run=False,
        auto_repair_qa=False,
    )
    rec = report.records[0]

    assert rec.status == "failed"
    assert rec.initial_qa_failed is True
    assert rec.repair_attempted is False
    assert engine.qa.calls == 1
