import pytest
from fastapi.testclient import TestClient

from api import app
import app.agents.router as agents_router_module

from app.agents import (
    AgentHeartbeat,
    AgentRegistry,
    AgentStateUpdate,
    AgentStatus,
)

@pytest.fixture(autouse=True)
def isolated_agent_api_registry(
    tmp_path,
    monkeypatch,
):
    registry = AgentRegistry(
        state_path=tmp_path / "agents.json",
    )

    monkeypatch.setattr(
        agents_router_module,
        "registry",
        registry,
    )

    return registry



def test_update_agent_state():
    registry = AgentRegistry()

    updated = registry.update_state(
        "codex",
        AgentStateUpdate(
            status=AgentStatus.RUNNING,
            current_task="TASK-017",
            project="data-eng-port",
            session_id="exec-123",
        ),
    )

    assert updated.status == AgentStatus.RUNNING
    assert updated.current_task == "TASK-017"
    assert updated.project == "data-eng-port"
    assert updated.session_id == "exec-123"
    assert updated.last_activity is not None


def test_agent_heartbeat():
    registry = AgentRegistry()

    updated = registry.heartbeat(
        "codex",
        AgentHeartbeat(
            current_task="TASK-018",
            project="data-eng-port",
            session_id="exec-456",
        ),
    )

    assert updated.heartbeat_at is not None
    assert updated.last_activity is not None
    assert updated.current_task == "TASK-018"
    assert updated.project == "data-eng-port"
    assert updated.session_id == "exec-456"


def test_heartbeat_recovers_offline_agent():
    registry = AgentRegistry()

    registry.update_state(
        "codex",
        AgentStateUpdate(
            status=AgentStatus.OFFLINE,
        ),
    )

    updated = registry.heartbeat(
        "codex",
        AgentHeartbeat(),
    )

    assert updated.status == AgentStatus.IDLE


def test_state_api():
    client = TestClient(app)

    response = client.post(
        "/api/agents/codex/state",
        json={
            "status": "running",
            "current_task": "TASK-017",
            "project": "data-eng-port",
            "session_id": "exec-api-1",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "running"
    assert payload["current_task"] == "TASK-017"
    assert payload["project"] == "data-eng-port"


def test_heartbeat_api():
    client = TestClient(app)

    response = client.post(
        "/api/agents/codex/heartbeat",
        json={
            "current_task": "TASK-018",
            "project": "data-eng-port",
            "session_id": "exec-api-2",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["heartbeat_at"] is not None
    assert payload["last_activity"] is not None


def test_unknown_agent_state_returns_404():
    client = TestClient(app)

    response = client.post(
        "/api/agents/not-real/state",
        json={"status": "running"},
    )

    assert response.status_code == 404


def test_unknown_agent_heartbeat_returns_404():
    client = TestClient(app)

    response = client.post(
        "/api/agents/not-real/heartbeat",
        json={},
    )

    assert response.status_code == 404
