import subprocess

import pytest

from app.execution.git_ops import GitOps


def _git(repo, *args):
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _repo(tmp_path):
    repo = tmp_path / "client-project"
    repo.mkdir()

    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "AI Agency Test")

    (repo / "baseline.txt").write_text("baseline", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "baseline")

    return repo


def test_interrupt_recovery_returns_to_clean_integration(tmp_path):
    repo = _repo(tmp_path)
    git = GitOps(repo)

    integration = "ai/integration/demo"
    task = "ai/task-001-demo"

    git.create_or_switch_integration(integration)
    integration_sha = git.head_sha()
    git.create_or_reset_branch_from(task, integration)

    (repo / "partial.txt").write_text("partial model work", encoding="utf-8")
    (repo / "baseline.txt").write_text("modified", encoding="utf-8")

    assert git.has_changes()

    git.recover_interrupted_task(task, integration)

    assert git.current_branch() == integration
    assert git.working_tree_clean()
    assert git.head_sha() == integration_sha
    assert not (repo / "partial.txt").exists()
    assert (repo / "baseline.txt").read_text(encoding="utf-8") == "baseline"


def test_interrupt_recovery_refuses_wrong_active_branch(tmp_path):
    repo = _repo(tmp_path)
    git = GitOps(repo)

    integration = "ai/integration/demo"
    git.create_or_switch_integration(integration)

    with pytest.raises(RuntimeError, match="current branch"):
        git.recover_interrupted_task(
            "ai/task-001-demo",
            integration,
        )


def test_interrupt_recovery_does_not_move_integration_history(tmp_path):
    repo = _repo(tmp_path)
    git = GitOps(repo)

    integration = "ai/integration/demo"
    task = "ai/task-001-demo"

    git.create_or_switch_integration(integration)

    (repo / "integration.txt").write_text("kept", encoding="utf-8")
    assert git.commit_all("integration checkpoint")

    integration_sha = git.head_sha()

    git.create_or_reset_branch_from(task, integration)
    (repo / "partial.txt").write_text("discard me", encoding="utf-8")

    git.recover_interrupted_task(task, integration)

    assert git.head_sha() == integration_sha
    assert (repo / "integration.txt").read_text(encoding="utf-8") == "kept"
    assert not (repo / "partial.txt").exists()


class _InterruptAdapter:
    binary = "dummy"

    def available(self):
        return True

    def run(self, *args, **kwargs):
        raise KeyboardInterrupt


def test_qa_repair_interrupt_recovers_repository(tmp_path):
    from app.execution.engine import ExecutionEngine

    repo = _repo(tmp_path)
    git = GitOps(repo)

    integration = "ai/integration/demo"
    git.create_or_switch_integration(integration)
    integration_sha = git.head_sha()

    engine = ExecutionEngine()
    engine.adapters["codex"] = _InterruptAdapter()

    with pytest.raises(KeyboardInterrupt):
        engine._attempt_qa_repair(
            root=repo,
            git=git,
            integration_branch=integration,
            task_id="TASK-007",
            task_text="Run deterministic QA",
            project_name="demo",
            results=[],
            attempt=1,
            primary_owner="codex",
            allow_fallback=False,
        )

    assert git.current_branch() == integration
    assert git.working_tree_clean()
    assert git.head_sha() == integration_sha


def test_existing_dirty_repo_is_rejected_before_execution(tmp_path):
    repo = _repo(tmp_path)
    git = GitOps(repo)

    (repo / "client-work.txt").write_text(
        "do not delete",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="belum di-commit"):
        git.ensure_baseline_commit()

    assert (repo / "client-work.txt").read_text(encoding="utf-8") == "do not delete"
