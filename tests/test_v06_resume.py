from pathlib import Path

from app.execution.git_ops import GitOps


def _commit(git: GitOps, message: str):
    git._run(["git", "add", "-A"])
    git._run([
        "git",
        "-c", "user.name=AI Agency",
        "-c", "user.email=ai-agency@local",
        "commit",
        "--allow-empty",
        "-m", message,
    ])


def test_completed_task_branch_is_detected_as_merged(tmp_path):
    root = Path(tmp_path)
    git = GitOps(root)
    git.ensure_repo()
    _commit(git, "chore: execution baseline")

    integration = "ai/integration/demo"
    task = "ai/task-001-initialize-project"

    git.create_or_switch_integration(integration)
    git.create_or_reset_branch_from(task, integration)
    (root / "app.txt").write_text("done", encoding="utf-8")
    _commit(git, "TASK-001: Initialize project")
    git.create_or_switch_integration(integration)
    git.merge_no_ff(task, "merge TASK-001: Initialize project")

    assert git.task_already_merged(task, integration) is True


def test_old_baseline_task_branch_is_not_treated_as_completed(tmp_path):
    root = Path(tmp_path)
    git = GitOps(root)
    git.ensure_repo()
    _commit(git, "chore: execution baseline")

    integration = "ai/integration/demo"
    task = "ai/task-002-quality-rules"

    git.create_or_switch_integration(integration)
    git.create_or_reset_branch_from(task, integration)

    # Reset the integration branch to the same baseline state as the task branch.
    git.create_or_switch_integration(integration)

    assert git.task_already_merged(task, integration) is False
