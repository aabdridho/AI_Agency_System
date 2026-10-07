from pathlib import Path

import app.workspace as workspace
from route_project import resolve_project_path


def configure_workspace(monkeypatch, tmp_path):
    root = tmp_path / "AI_Agency_System_Specification"
    system = root / "AI_Agency_System"
    output = root / "AI_Output"

    system.mkdir(parents=True)
    output.mkdir(parents=True)

    monkeypatch.setattr(workspace, "SYSTEM_ROOT", system)
    monkeypatch.setattr(workspace, "SPEC_ROOT", root)
    monkeypatch.setattr(workspace, "OUTPUT_ROOT", output)

    return root, system, output


def test_resolve_canonical_project_by_name(tmp_path, monkeypatch):
    _, _, output = configure_workspace(
        monkeypatch,
        tmp_path,
    )

    project = output / "data-eng-port"
    project.mkdir(parents=True)

    resolved = resolve_project_path("data-eng-port")

    assert resolved == project.resolve()


def test_resolve_absolute_project_path(tmp_path, monkeypatch):
    configure_workspace(
        monkeypatch,
        tmp_path,
    )

    project = tmp_path / "external-project"
    project.mkdir()

    resolved = resolve_project_path(str(project))

    assert resolved == project.resolve()


def test_missing_project_raises_file_not_found(
    tmp_path,
    monkeypatch,
):
    configure_workspace(
        monkeypatch,
        tmp_path,
    )

    try:
        resolve_project_path(
            "project-that-does-not-exist"
        )
    except FileNotFoundError as exc:
        assert "Project folder tidak ditemukan" in str(exc)
    else:
        raise AssertionError(
            "Expected FileNotFoundError"
        )


def test_legacy_v04_location_is_not_resolved(
    tmp_path,
    monkeypatch,
):
    root, _, _ = configure_workspace(
        monkeypatch,
        tmp_path,
    )

    legacy = (
        root
        / "agency_router_v0_4"
        / "generated_projects"
        / "data-eng-port"
    )

    legacy.mkdir(parents=True)

    try:
        resolve_project_path("data-eng-port")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError(
            "Legacy V0.4 project should no longer resolve."
        )
