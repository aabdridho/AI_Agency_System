from unittest.mock import patch

from app.command_resolver import resolve_node_cli


def test_windows_prefers_cmd_shim():
    def fake_which(name):
        return f"C:/node/{name}" if name in {"npm.cmd", "npm"} else None

    with patch("app.command_resolver.sys.platform", "win32"), \
         patch("app.command_resolver.shutil.which", side_effect=fake_which):
        assert resolve_node_cli("npm") == "npm.cmd"


def test_windows_falls_back_to_plain_binary():
    def fake_which(name):
        return "C:/node/npm" if name == "npm" else None

    with patch("app.command_resolver.sys.platform", "win32"), \
         patch("app.command_resolver.shutil.which", side_effect=fake_which):
        assert resolve_node_cli("npm") == "npm"


def test_non_windows_uses_plain_binary():
    def fake_which(name):
        return "/usr/bin/npm" if name == "npm" else None

    with patch("app.command_resolver.sys.platform", "linux"), \
         patch("app.command_resolver.shutil.which", side_effect=fake_which):
        assert resolve_node_cli("npm") == "npm"


def test_missing_node_cli_returns_none():
    with patch("app.command_resolver.sys.platform", "win32"), \
         patch("app.command_resolver.shutil.which", return_value=None):
        assert resolve_node_cli("npx") is None
