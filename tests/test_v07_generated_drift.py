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


def test_next_env_generated_drift_is_restored(tmp_path):
    root = Path(tmp_path)
    git = GitOps(root)
    git.ensure_repo()
    (root / "next-env.d.ts").write_text("dev version", encoding="utf-8")
    _commit(git, "chore: execution baseline")

    (root / "next-env.d.ts").write_text("build generated version", encoding="utf-8")
    assert git.has_changes()

    git.ensure_baseline_commit()

    assert not git.has_changes()
    assert (root / "next-env.d.ts").read_text(encoding="utf-8") == "dev version"


def test_generated_drift_is_not_restored_when_real_source_is_dirty(tmp_path):
    root = Path(tmp_path)
    git = GitOps(root)
    git.ensure_repo()
    (root / "next-env.d.ts").write_text("dev version", encoding="utf-8")
    (root / "src.ts").write_text("one", encoding="utf-8")
    _commit(git, "chore: execution baseline")

    (root / "next-env.d.ts").write_text("generated", encoding="utf-8")
    (root / "src.ts").write_text("two", encoding="utf-8")

    try:
        git.ensure_baseline_commit()
    except RuntimeError as exc:
        assert "src.ts" in str(exc)
    else:
        raise AssertionError("dirty source must still block execution")

    assert (root / "next-env.d.ts").read_text(encoding="utf-8") == "generated"
