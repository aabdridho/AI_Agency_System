from datetime import datetime, timedelta, timezone

from app.agents import (
    AgentHeartbeat,
    AgentRegistry,
    AgentStateUpdate,
    AgentStatus,
)


def test_stale_running_agent_becomes_offline():
    registry = AgentRegistry()

    registry.update_state(
        "codex",
        AgentStateUpdate(
            status=AgentStatus.RUNNING,
            current_task="TASK-001",
            project="demo",
            run_id="run-a",
            session_id="run-a:implementation:demo:TASK-001",
        ),
    )

    agent = registry._agents["codex"]

    agent.heartbeat_at = (
        datetime.now(timezone.utc)
        - timedelta(seconds=30)
    ).isoformat()

    observed = registry.get_agent("codex")

    assert observed.status == AgentStatus.OFFLINE
    assert observed.project == "demo"
    assert observed.run_id == "run-a"


def test_fresh_running_agent_stays_running():
    registry = AgentRegistry()

    registry.update_state(
        "codex",
        AgentStateUpdate(
            status=AgentStatus.RUNNING,
            current_task="TASK-001",
            project="demo",
        ),
    )

    registry.heartbeat(
        "codex",
        AgentHeartbeat(),
    )

    observed = registry.get_agent("codex")

    assert observed.status == AgentStatus.RUNNING


def test_waiting_agent_is_not_expired_by_heartbeat_age():
    registry = AgentRegistry()

    registry.update_state(
        "deterministic-qa",
        AgentStateUpdate(
            status=AgentStatus.WAITING,
            current_task="TASK-001",
            project="demo",
            run_id="run-a",
        ),
    )

    agent = registry._agents["deterministic-qa"]

    agent.heartbeat_at = (
        datetime.now(timezone.utc)
        - timedelta(hours=1)
    ).isoformat()

    observed = registry.get_agent(
        "deterministic-qa"
    )

    assert observed.status == AgentStatus.WAITING


def test_offline_agent_keeps_execution_context_until_recovery():
    registry = AgentRegistry()

    registry.update_state(
        "codex",
        AgentStateUpdate(
            status=AgentStatus.RUNNING,
            current_task="TASK-001",
            project="demo",
            run_id="run-a",
            session_id="run-a:implementation:demo:TASK-001",
        ),
    )

    agent = registry._agents["codex"]

    agent.heartbeat_at = (
        datetime.now(timezone.utc)
        - timedelta(seconds=30)
    ).isoformat()

    observed = registry.get_agent("codex")

    assert observed.status == AgentStatus.OFFLINE
    assert observed.current_task == "TASK-001"
    assert observed.project == "demo"
    assert observed.run_id == "run-a"
    assert (
        observed.session_id
        == "run-a:implementation:demo:TASK-001"
    )
