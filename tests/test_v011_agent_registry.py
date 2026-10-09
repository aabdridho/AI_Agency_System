import pytest
from fastapi.testclient import TestClient

from api import app
import app.agents.router as agents_router_module

from app.agents import AgentRegistry, AgentStatus

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



def test_registry_contains_bootstrap_agents():
    registry = AgentRegistry()

    agents = registry.list_agents()

    ids = {agent.id for agent in agents}

    assert "codex" in ids
    assert "claude-code" in ids
    assert "deterministic-qa" in ids
    assert "deployment-guard" in ids


def test_agents_start_idle():
    registry = AgentRegistry()

    for agent in registry.list_agents():
        assert agent.status == AgentStatus.IDLE


def test_registry_get_agent():
    registry = AgentRegistry()

    agent = registry.get_agent("codex")

    assert agent.id == "codex"
    assert agent.provider == "openai"
    assert agent.role == "backend_engineering"


def test_agents_api():
    client = TestClient(app)

    response = client.get("/api/agents")

    assert response.status_code == 200

    payload = response.json()

    assert len(payload) >= 4

    ids = {agent["id"] for agent in payload}

    assert "codex" in ids
    assert "claude-code" in ids


def test_agent_detail_api():
    client = TestClient(app)

    response = client.get("/api/agents/codex")

    assert response.status_code == 200

    payload = response.json()

    assert payload["id"] == "codex"
    assert payload["status"] == "idle"


def test_unknown_agent_returns_404():
    client = TestClient(app)

    response = client.get("/api/agents/not-real")

    assert response.status_code == 404
