from pathlib import Path
from app.delivery.checker import DeliveryChecker


def _init_git(repo: Path):
    import subprocess
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)


def _commit_all(repo: Path):
    import subprocess
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=repo, check=True, capture_output=True)


def test_environment_contract_detects_missing_env_example_entry(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "route.ts").write_text(
        "const x = process.env.RESEND_API_KEY; const y = process.env.CONTACT_EMAIL_TO;",
        encoding="utf-8",
    )
    (tmp_path / ".env.example").write_text("RESEND_API_KEY=\n", encoding="utf-8")
    check = DeliveryChecker(tmp_path).environment_contract()
    assert check.status == "blocker"
    assert "CONTACT_EMAIL_TO" in check.detail


def test_environment_contract_passes_when_documented(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "route.ts").write_text("const x = process.env.RESEND_API_KEY;", encoding="utf-8")
    (tmp_path / ".env.example").write_text("RESEND_API_KEY=\n", encoding="utf-8")
    assert DeliveryChecker(tmp_path).environment_contract().status == "pass"


def test_placeholder_content_blocks_known_placeholder_markers(tmp_path):
    (tmp_path / "src" / "content").mkdir(parents=True)
    (tmp_path / "src" / "content" / "hero.ts").write_text('export const hero = "Your Name";', encoding="utf-8")
    assert DeliveryChecker(tmp_path).placeholder_content().status == "blocker"


def test_unresolved_deployment_target_blocks(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "architecture.md").write_text(
        "- deployment_target: to_be_decided_internally",
        encoding="utf-8",
    )
    check = DeliveryChecker(tmp_path).unresolved_project_decisions()
    assert check.status == "blocker"


def test_tracked_env_file_blocks_delivery(tmp_path):
    _init_git(tmp_path)
    (tmp_path / ".env").write_text("SECRET=x", encoding="utf-8")
    _commit_all(tmp_path)
    check = DeliveryChecker(tmp_path).tracked_secret_files()
    assert check.status == "blocker"
    assert ".env" in check.detail


def test_env_example_is_allowed(tmp_path):
    _init_git(tmp_path)
    (tmp_path / ".env.example").write_text("SECRET=\n", encoding="utf-8")
    _commit_all(tmp_path)
    assert DeliveryChecker(tmp_path).tracked_secret_files().status == "pass"
