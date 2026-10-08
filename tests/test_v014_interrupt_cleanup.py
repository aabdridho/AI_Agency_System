import pytest

from app.execution.engine import ExecutionEngine


class _InterruptAdapter:
    binary = "dummy"

    def available(self):
        return True

    def run(self, *args, **kwargs):
        raise KeyboardInterrupt


class _Registry:
    def __init__(self):
        self.states = []

    def update_state(self, agent_id, update):
        self.states.append(
            (
                agent_id,
                update.status.value,
                update.current_task,
            )
        )

    def heartbeat(self, *args, **kwargs):
        pass


def test_keyboard_interrupt_returns_agent_to_idle():
    registry = _Registry()

    engine = ExecutionEngine(
        agent_registry=registry,
    )

    engine.adapters["codex"] = _InterruptAdapter()

    engine._agent_start(
        "codex",
        project_name="demo",
        task_id="TASK-001",
    )

    with pytest.raises(KeyboardInterrupt):
        try:
            engine._run_adapter(
                engine.adapters["codex"],
                None,
                "test",
                model=None,
                effort=None,
            )
        except KeyboardInterrupt:
            engine._agent_idle("codex")
            raise

    assert registry.states[-1][0] == "codex"
    assert registry.states[-1][1] == "idle"
