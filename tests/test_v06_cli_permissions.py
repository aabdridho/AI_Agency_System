from app.execution.adapters import ClaudeCodeAdapter, CodexAdapter
from app.execution.qa import DeterministicQA


def test_claude_noninteractive_accepts_edits():
    cmd = ClaudeCodeAdapter().build_command("hello")
    assert "--permission-mode" in cmd
    assert "acceptEdits" in cmd
    assert "--permission-prompts" in cmd
    assert "none" in cmd


def test_codex_workspace_write_mode():
    cmd = CodexAdapter().build_command("hello")
    # Codex v0.160.1 makes --approve-for-me mutually exclusive with --sandbox
    # and documents that it routes approvals through workspace-write.
    assert "--approve-for-me" in cmd
    assert "--sandbox" not in cmd


def test_windows_npm_cmd_is_preferred(tmp_path, monkeypatch):
    (tmp_path / "package.json").write_text(
        '{"scripts":{"build":"vite build","lint":"eslint ."}}',
        encoding="utf-8",
    )

    def fake_which(name):
        if name == "npm.cmd":
            return r"C:\\Program Files\\nodejs\\npm.cmd"
        if name == "python":
            return r"C:\\Python\\python.exe"
        return None

    monkeypatch.setattr("shutil.which", fake_which)
    commands = DeterministicQA().detect_commands(tmp_path)
    assert ["npm.cmd", "run", "lint"] in commands
    assert ["npm.cmd", "run", "build"] in commands
