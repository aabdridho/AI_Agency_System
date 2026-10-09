from app.agents import (
    AgentHeartbeat,
    AgentRegistry,
    AgentStateUpdate,
    AgentStatus,
)
from app.execution.engine import ExecutionEngine


def test_agent_state_tracks_run_id():
    registry = AgentRegistry()

    updated = registry.update_state(
        "codex",
        AgentStateUpdate(
            status=AgentStatus.RUNNING,
            current_task="TASK-001",
            project="demo",
            run_id="run-a",
            session_id="run-a:implementation:demo:TASK-001",
        ),
    )

    assert updated.project == "demo"
    assert updated.run_id == "run-a"
    assert updated.current_task == "TASK-001"
    assert updated.session_id == "run-a:implementation:demo:TASK-001"


def test_idle_state_clears_run_context():
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

    updated = registry.update_state(
        "codex",
        AgentStateUpdate(
            status=AgentStatus.IDLE,
        ),
    )

    assert updated.status == AgentStatus.IDLE
    assert updated.current_task is None
    assert updated.project is None
    assert updated.run_id is None
    assert updated.session_id is None


def test_empty_heartbeat_preserves_run_context():
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

    updated = registry.heartbeat(
        "codex",
        AgentHeartbeat(),
    )

    assert updated.run_id == "run-a"
    assert updated.project == "demo"
    assert updated.current_task == "TASK-001"
    assert updated.session_id == "run-a:implementation:demo:TASK-001"


def test_execution_agent_session_is_run_scoped():
    engine = ExecutionEngine(
        run_id="run-a",
    )

    session = engine._agent_session(
        "demo",
        "TASK-001",
        phase="implementation",
    )

    assert session == "run-a:implementation:demo:TASK-001"


def test_execution_agent_session_keeps_legacy_shape_without_run():
    engine = ExecutionEngine()

    session = engine._agent_session(
        "demo",
        "TASK-001",
        phase="implementation",
    )

    assert session == "implementation:demo:TASK-001"
