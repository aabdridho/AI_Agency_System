from pathlib import Path
from types import SimpleNamespace

import app.execution.engine as engine_module

from app.agents import (
    AgentRegistry,
    AgentStateUpdate,
    AgentStatus,
)
from app.execution.engine import ExecutionEngine


class FakeGitOps:
    def __init__(self, root):
        self.root = Path(root)
        self.head = "base"

    def integration_branch(self, project_name):
        return f"ai/integration/{project_name}"

    def ensure_baseline_commit(self):
        return None

    def create_or_switch_integration(self, branch):
        return None

    def sanitize_branch(self, task_id, task_text):
        return f"ai/{task_id.lower()}"

    def task_already_merged(self, task_branch, integration_branch):
        return False

    def create_or_reset_branch_from(self, branch, base):
        self.head = "base"

    def head_sha(self):
        return self.head

    def has_changes(self):
        return True

    def commit_all(self, message):
        self.head = "task"
        return True

    def merge_no_ff(self, branch, message):
        self.head = "integration"

    def is_ancestor(self, commit, branch):
        return True

    def reset_hard_to(self, ref):
        self.head = "base"

    def ref_sha(self, ref):
        return "base"

    def repair_branch(self, task_id, attempt):
        return f"ai/repair/{task_id.lower()}-{attempt}"


def decision(
    owner="codex",
    fallback=None,
    escalations=0,
):
    return SimpleNamespace(
        task_id="TASK-001",
        task_text="Implement test feature",
        primary_owner=owner,
        fallback_owner=fallback,
        max_escalations=escalations,
    )


def plan(item):
    return SimpleNamespace(
        project_name="demo-project",
        decisions=[item],
    )


def test_execution_agent_runs_then_returns_idle(
    tmp_path,
    monkeypatch,
):
    registry = AgentRegistry()

    engine = ExecutionEngine(
        agent_registry=registry,
    )

    monkeypatch.setattr(
        engine_module,
        "GitOps",
        FakeGitOps,
    )

    engine.prompt_builder.build = (
        lambda root, task: "prompt"
    )

    class Adapter:
        binary = "fake"

        def available(self):
            return True

        def build_command(self, prompt):
            return [self.binary, "exec", prompt]

        def run(self, root, prompt, stream=True):
            agent = registry.get_agent("codex")

            assert agent.status == AgentStatus.RUNNING
            assert agent.current_task == "TASK-001"
            assert agent.project == "demo-project"

            return SimpleNamespace(
                returncode=0,
                stdout="ok",
                stderr="",
            )

    engine.adapters["codex"] = Adapter()

    report = engine.execute(
        plan(decision()),
        tmp_path,
        dry_run=False,
    )

    assert report.records[0].status == "success"

    agent = registry.get_agent("codex")

    assert agent.status == AgentStatus.IDLE
    assert agent.current_task is None
    assert agent.project is None
    assert agent.session_id is None


def test_dry_run_does_not_mutate_agent_state(
    tmp_path,
    monkeypatch,
):
    registry = AgentRegistry()

    engine = ExecutionEngine(
        agent_registry=registry,
    )

    monkeypatch.setattr(
        engine_module,
        "GitOps",
        FakeGitOps,
    )

    engine.prompt_builder.build = (
        lambda root, task: "prompt"
    )

    report = engine.execute(
        plan(decision()),
        tmp_path,
        dry_run=True,
    )

    assert report.records[0].status == "dry_run"

    agent = registry.get_agent("codex")

    assert agent.status == AgentStatus.IDLE
    assert agent.current_task is None


def test_fallback_changes_live_agent_owner(
    tmp_path,
    monkeypatch,
):
    registry = AgentRegistry()

    engine = ExecutionEngine(
        agent_registry=registry,
    )

    monkeypatch.setattr(
        engine_module,
        "GitOps",
        FakeGitOps,
    )

    engine.prompt_builder.build = (
        lambda root, task: "prompt"
    )

    class Primary:
        binary = "fake"

        def available(self):
            return True

        def build_command(self, prompt):
            return [self.binary, "exec", prompt]

        def run(self, root, prompt, stream=True):
            assert (
                registry.get_agent("codex").status
                == AgentStatus.RUNNING
            )

            return SimpleNamespace(
                returncode=1,
                stdout="",
                stderr="failed",
            )

    class Fallback:
        binary = "fake"

        def available(self):
            return True

        def build_command(self, prompt):
            return [self.binary, "exec", prompt]

        def run(self, root, prompt, stream=True):
            assert (
                registry.get_agent("codex").status
                == AgentStatus.ERROR
            )

            claude = registry.get_agent(
                "claude-code"
            )

            assert claude.status == AgentStatus.RUNNING

            return SimpleNamespace(
                returncode=0,
                stdout="fixed",
                stderr="",
            )

    engine.adapters["codex"] = Primary()
    engine.adapters["claude_code"] = Fallback()

    report = engine.execute(
        plan(
            decision(
                owner="codex",
                fallback="claude_code",
                escalations=1,
            )
        ),
        tmp_path,
        dry_run=False,
    )

    assert report.records[0].status == "success"
    assert report.records[0].escalated is True

    assert (
        registry.get_agent("codex").status
        == AgentStatus.ERROR
    )

    assert (
        registry.get_agent("claude-code").status
        == AgentStatus.IDLE
    )


def test_deterministic_qa_lifecycle(
    tmp_path,
    monkeypatch,
):
    registry = AgentRegistry()

    engine = ExecutionEngine(
        agent_registry=registry,
    )

    monkeypatch.setattr(
        engine_module,
        "GitOps",
        FakeGitOps,
    )

    engine.prompt_builder.build = (
        lambda root, task: "prompt"
    )

    class QA:
        def profile_for(self, task):
            return SimpleNamespace(name="generic")

        def run(self, root, task=None):
            qa = registry.get_agent(
                "deterministic-qa"
            )

            assert qa.status == AgentStatus.RUNNING
            assert qa.current_task == "TASK-001"

            return [
                (
                    ["check"],
                    SimpleNamespace(
                        returncode=0,
                        stdout="ok",
                        stderr="",
                    ),
                )
            ]

    engine.qa = QA()

    report = engine.execute(
        plan(
            decision(
                owner="deterministic_qa",
            )
        ),
        tmp_path,
        dry_run=False,
    )

    assert report.records[0].status == "success"

    qa = registry.get_agent(
        "deterministic-qa"
    )

    assert qa.status == AgentStatus.IDLE


def test_persistent_registry_is_shared_between_instances(
    tmp_path,
):
    state_file = tmp_path / "agents.json"

    first = AgentRegistry(
        state_path=state_file,
    )

    second = AgentRegistry(
        state_path=state_file,
    )

    first.update_state(
        "codex",
        AgentStateUpdate(
            status=AgentStatus.RUNNING,
            current_task="TASK-099",
            project="shared-project",
            session_id="shared-session",
        ),
    )

    observed = second.get_agent("codex")

    assert observed.status == AgentStatus.RUNNING
    assert observed.current_task == "TASK-099"
    assert observed.project == "shared-project"
    assert observed.session_id == "shared-session"
