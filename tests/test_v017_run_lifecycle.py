from types import SimpleNamespace

import pytest

from app.execution.events import ExecutionEventLedger
from app.orchestration.orchestrator import ProjectOrchestrator


def _orchestrator(tmp_path):
    runtime = tmp_path / "runtime_data"
    output = tmp_path / "AI_Output"
    output.mkdir()

    orchestrator = ProjectOrchestrator(
        runtime_root=runtime,
        output_root=output,
    )

    project = output / "demo"
    project.mkdir()

    return orchestrator


def _install_execution_boundary(
    monkeypatch,
    orchestrator,
    *,
    report=None,
    error=None,
):
    plan = SimpleNamespace(
        project_name="demo",
        decisions=[
            SimpleNamespace(task_id="TASK-001"),
        ],
    )

    class FakeRoutingEngine:
        def build_plan(self, root):
            return plan

    class FakeExecutionEngine:
        def __init__(
            self,
            *,
            usage_ledger,
            event_ledger,
            run_id,
        ):
            self.run_id = run_id

        def execute(
            self,
            plan,
            root,
            *,
            dry_run,
            allow_escalation,
        ):
            if error is not None:
                raise error

            return report

    class FakeExecutionStorage:
        def save(self, execution_report, runtime_root):
            return (
                runtime_root
                / "execution"
                / "demo"
                / "execution_report.json"
            )

    monkeypatch.setattr(
        "app.orchestration.orchestrator.RoutingEngine",
        FakeRoutingEngine,
    )

    monkeypatch.setattr(
        "app.orchestration.orchestrator.ExecutionEngine",
        FakeExecutionEngine,
    )

    monkeypatch.setattr(
        "app.orchestration.orchestrator.ExecutionStorage",
        FakeExecutionStorage,
    )

    monkeypatch.setattr(
        orchestrator,
        "execution_preflight",
        lambda project_name: [],
    )

    completed_state = SimpleNamespace(
        status="completed",
        current_stage="delivery",
    )

    monkeypatch.setattr(
        orchestrator,
        "resume",
        lambda project_name: completed_state,
    )

    return completed_state


def _events(orchestrator):
    return ExecutionEventLedger(
        orchestrator.runtime_root / "execution"
    ).read("demo")


def test_run_execution_emits_started_then_completed(
    tmp_path,
    monkeypatch,
):
    orchestrator = _orchestrator(tmp_path)

    report = SimpleNamespace(
        records=[],
    )

    expected_state = _install_execution_boundary(
        monkeypatch,
        orchestrator,
        report=report,
    )

    state = orchestrator.run_execution("demo")

    assert state is expected_state

    events = _events(orchestrator)

    assert [
        event.event_type
        for event in events
    ] == [
        "run.started",
        "run.completed",
    ]

    assert [
        event.status
        for event in events
    ] == [
        "running",
        "success",
    ]

    assert events[0].run_id
    assert events[1].run_id == events[0].run_id

    assert [
        event.sequence
        for event in events
    ] == [1, 2]

    assert events[0].metadata["task_count"] == 1
    assert events[1].metadata["record_count"] == 0
    assert events[1].metadata["failed_record_count"] == 0


def test_run_execution_completed_can_report_failed_records(
    tmp_path,
    monkeypatch,
):
    orchestrator = _orchestrator(tmp_path)

    report = SimpleNamespace(
        records=[
            SimpleNamespace(
                status="failed",
            ),
            SimpleNamespace(
                status="success",
            ),
        ],
    )

    _install_execution_boundary(
        monkeypatch,
        orchestrator,
        report=report,
    )

    orchestrator.run_execution("demo")

    events = _events(orchestrator)

    assert [
        event.event_type
        for event in events
    ] == [
        "run.started",
        "run.completed",
    ]

    completed = events[-1]

    assert completed.status == "failed"
    assert completed.metadata["record_count"] == 2
    assert completed.metadata["failed_record_count"] == 1


def test_run_execution_emits_failed_and_reraises_exception(
    tmp_path,
    monkeypatch,
):
    orchestrator = _orchestrator(tmp_path)

    _install_execution_boundary(
        monkeypatch,
        orchestrator,
        error=RuntimeError("engine exploded"),
    )

    with pytest.raises(
        RuntimeError,
        match="engine exploded",
    ):
        orchestrator.run_execution("demo")

    events = _events(orchestrator)

    assert [
        event.event_type
        for event in events
    ] == [
        "run.started",
        "run.failed",
    ]

    failed = events[-1]

    assert failed.status == "failed"
    assert failed.detail == "engine exploded"
    assert (
        failed.metadata["exception_type"]
        == "RuntimeError"
    )

    assert failed.run_id == events[0].run_id
    assert failed.sequence == 2


def test_run_execution_emits_failed_and_reraises_keyboard_interrupt(
    tmp_path,
    monkeypatch,
):
    orchestrator = _orchestrator(tmp_path)

    _install_execution_boundary(
        monkeypatch,
        orchestrator,
        error=KeyboardInterrupt(),
    )

    with pytest.raises(KeyboardInterrupt):
        orchestrator.run_execution("demo")

    events = _events(orchestrator)

    assert [
        event.event_type
        for event in events
    ] == [
        "run.started",
        "run.failed",
    ]

    failed = events[-1]

    assert failed.status == "failed"
    assert failed.detail == "KeyboardInterrupt"
    assert (
        failed.metadata["exception_type"]
        == "KeyboardInterrupt"
    )
