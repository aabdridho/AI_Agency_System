import threading
import time
from types import SimpleNamespace

import pytest

from app.agents import AgentRegistry
from app.execution.engine import ExecutionEngine


class _BlockingAdapter:
    def __init__(self, release):
        self.release = release

    def run(self, root, prompt, stream=True):
        self.release.wait(timeout=1.0)

        return SimpleNamespace(
            returncode=0,
            stdout="ok",
            stderr="",
        )


class _InterruptAdapter:
    def run(self, root, prompt, stream=True):
        raise KeyboardInterrupt


def test_adapter_runtime_lease_refreshes_heartbeat():
    registry = AgentRegistry()

    engine = ExecutionEngine(
        agent_registry=registry,
        run_id="run-lease",
    )

    engine.AGENT_HEARTBEAT_INTERVAL_SECONDS = 0.02

    release = threading.Event()

    engine._agent_start(
        "codex",
        project_name="demo",
        task_id="TASK-001",
        phase="implementation",
    )

    before = registry.get_agent("codex").heartbeat_at

    timer = threading.Timer(
        0.09,
        release.set,
    )

    timer.start()

    try:
        result = engine._run_adapter_with_lease(
            "codex",
            _BlockingAdapter(release),
            None,
            "prompt",
            project_name="demo",
            task_id="TASK-001",
            phase="implementation",
            model=None,
            effort=None,
        )
    finally:
        timer.cancel()
        release.set()

    after = registry.get_agent("codex").heartbeat_at

    assert result.returncode == 0
    assert before is not None
    assert after is not None
    assert after != before


def test_runtime_lease_preserves_keyboard_interrupt():
    registry = AgentRegistry()

    engine = ExecutionEngine(
        agent_registry=registry,
        run_id="run-interrupt",
    )

    engine.AGENT_HEARTBEAT_INTERVAL_SECONDS = 0.01

    with pytest.raises(KeyboardInterrupt):
        engine._run_adapter_with_lease(
            "codex",
            _InterruptAdapter(),
            None,
            "prompt",
            project_name="demo",
            task_id="TASK-002",
            phase="implementation",
            model=None,
            effort=None,
        )


def test_runtime_lease_worker_stops_after_adapter_returns():
    registry = AgentRegistry()

    engine = ExecutionEngine(
        agent_registry=registry,
        run_id="run-stop",
    )

    engine.AGENT_HEARTBEAT_INTERVAL_SECONDS = 0.01

    class Adapter:
        def run(self, root, prompt, stream=True):
            return SimpleNamespace(
                returncode=0,
                stdout="ok",
                stderr="",
            )

    engine._run_adapter_with_lease(
        "codex",
        Adapter(),
        None,
        "prompt",
        project_name="demo",
        task_id="TASK-003",
        phase="implementation",
        model=None,
        effort=None,
    )

    leaked = [
        thread.name
        for thread in threading.enumerate()
        if thread.name.startswith(
            "agent-heartbeat:demo:TASK-003:"
        )
    ]

    assert leaked == []
