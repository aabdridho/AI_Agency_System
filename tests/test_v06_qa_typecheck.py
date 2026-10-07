
from app.execution.qa import DeterministicQA


def test_node_typecheck_is_detected(tmp_path, monkeypatch):
    (tmp_path / "package.json").write_text(
        '{"scripts":{"lint":"eslint .","typecheck":"tsc --noEmit","test":"node --test","build":"next build"}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "shutil.which",
        lambda name: "C:/Program Files/nodejs/npm.cmd" if name == "npm.cmd" else None,
    )
    commands = DeterministicQA().detect_commands(tmp_path)
    assert ["npm.cmd", "run", "typecheck"] in commands
