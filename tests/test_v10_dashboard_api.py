import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api
from app.dashboard import DashboardService


TASK_MD = """# Tasks
- [ ] Initialize project structure and development environment
- [ ] Implement `hero` section
- [ ] Submit form data to API endpoint
- [ ] Run deterministic validation (lint/tests)
"""


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data) if not isinstance(data, str) else data, encoding="utf-8")


@pytest.fixture
def env(tmp_path):
    runtime, output = tmp_path / "runtime_data", tmp_path / "AI_Output"
    svc = DashboardService(runtime_root=runtime, output_root=output)
    api.app.dependency_overrides[api.get_dashboard] = lambda: svc
    yield runtime, output, TestClient(api.app)
    api.app.dependency_overrides.clear()


def _project_with_tasks(output: Path, name="kafe-site"):
    root = output / name
    _write(root / "docs" / "requirement.md", "# Requirement")
    _write(root / "docs" / "task.md", TASK_MD)
    return root


def test_empty_workspace_lists_nothing(env):
    _, _, client = env
    assert client.get("/api/projects").json() == []


def test_project_with_tasks_gets_preview_routing_without_writing(env):
    runtime, output, client = env
    _project_with_tasks(output)

    projects = client.get("/api/projects").json()
    assert [p["name"] for p in projects] == ["kafe-site"]
    stages = {s["key"]: s["status"] for s in projects[0]["stages"]}
    assert stages["documentation"] == "done"
    assert stages["routing"] == "wait"

    detail = client.get("/api/projects/kafe-site").json()
    assert detail["routing_source"] == "preview"
    owners = [d["primary_owner"] for d in detail["routing"]["decisions"]]
    assert owners == ["codex", "claude_code", "codex", "deterministic_qa"]
    assert not (runtime / "routing").exists()  # preview never writes


def test_save_routing_persists_plan(env):
    runtime, output, client = env
    _project_with_tasks(output)

    res = client.post("/api/projects/kafe-site/route")
    assert res.status_code == 200
    assert res.json()["routing_source"] == "saved"
    assert (runtime / "routing" / "kafe-site" / "routing_plan.json").is_file()
    stages = {s["key"]: s["status"] for s in res.json()["stages"]}
    assert stages["routing"] == "done"


def test_save_routing_without_task_md_is_conflict(env):
    _, output, client = env
    (output / "empty-proj").mkdir(parents=True)
    assert client.post("/api/projects/empty-proj/route").status_code == 409


def test_stage_states_follow_reports(env):
    runtime, output, client = env
    _project_with_tasks(output)
    _write(runtime / "execution" / "kafe-site" / "execution_report.json", {
        "project_name": "kafe-site", "dry_run": False,
        "records": [
            {"task_id": "TASK-001", "owner": "codex", "branch": "b", "status": "success"},
            {"task_id": "TASK-002", "owner": "claude_code", "branch": "b", "status": "failed"},
        ],
    })
    _write(runtime / "delivery" / "kafe-site" / "delivery_report.json", {
        "project_name": "kafe-site", "project_root": "x", "overall_status": "blocked",
        "checks": [{"check_id": "c", "title": "t", "status": "blocker", "detail": "d"}],
    })
    _write(runtime / "deployment" / "kafe-site" / "deployment_plan.json", {
        "project_name": "kafe-site", "project_root": "x", "provider": "vercel",
        "mode": "dry-run", "status": "ready",
    })

    stages = {s["key"]: (s["status"], s["detail"]) for s in client.get("/api/projects/kafe-site").json()["stages"]}
    assert stages["execution"] == ("fail", "1 task gagal")
    assert stages["delivery"] == ("fail", "1 blocker")
    assert stages["deployment"] == ("wait", "tunggu approval")


def test_runtime_only_project_is_listed(env):
    runtime, _, client = env
    _write(runtime / "delivery" / "old-proj" / "delivery_report.json", {
        "project_name": "old-proj", "project_root": "x", "overall_status": "ready",
    })
    detail = client.get("/api/projects/old-proj").json()
    assert detail["has_workspace"] is False
    assert {s["key"]: s["status"] for s in detail["stages"]}["delivery"] == "done"


@pytest.mark.parametrize("name", ["..", "a..b", "-x", "a b"])
def test_bad_names_are_not_found(env, name):
    _, _, client = env
    assert client.get(f"/api/projects/{name}").status_code == 404


def test_traversal_name_never_reads_outside_root(env, tmp_path):
    _, _, client = env
    _write(tmp_path / "secret" / "docs" / "task.md", TASK_MD)
    assert client.get("/api/projects/..%2Fsecret").status_code == 404


def test_config_defaults_then_roundtrip(env):
    runtime, _, client = env
    assert client.get("/api/config").json() == {"source": "default", "tiers": None}

    body = {"tiers": {"triage": {"model": "rules", "effort": "low"},
                      "deep": {"model": "opus", "effort": "high"}}}
    assert client.put("/api/config", json=body).status_code == 200
    assert (runtime / "config" / "tiers.json").is_file()
    got = client.get("/api/config").json()
    assert got["source"] == "saved"
    assert got["tiers"]["deep"] == {"model": "opus", "effort": "high"}


@pytest.mark.parametrize("tiers", [
    {"deep": {"model": "gpt-9", "effort": "high"}},
    {"deep": {"model": "opus", "effort": "max"}},
    {"bogus": {"model": "opus", "effort": "high"}},
    {"build": {"model": "rules", "effort": "low"}},
])
def test_config_rejects_invalid(env, tiers):
    _, _, client = env
    assert client.put("/api/config", json={"tiers": tiers}).status_code == 422


def test_existing_endpoints_still_work(env):
    _, _, client = env
    assert client.get("/health").json()["status"] == "ok"
