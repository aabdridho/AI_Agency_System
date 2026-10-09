import json

from app.execution.events import ExecutionEventLedger


def test_execution_event_ledger_roundtrip(tmp_path):
    ledger = ExecutionEventLedger(tmp_path)

    path = ledger.append(
        project_name="demo",
        task_id="TASK-001",
        event_type="primary.started",
        phase="primary",
        status="running",
        owner="codex",
        model="gpt-6.1-sol",
        effort="medium",
        metadata={
            "route": "build",
        },
    )

    assert path.is_file()

    events = ledger.read("demo")

    assert len(events) == 1

    event = events[0]

    assert event.project_name == "demo"
    assert event.task_id == "TASK-001"
    assert event.event_type == "primary.started"
    assert event.phase == "primary"
    assert event.status == "running"
    assert event.owner == "codex"
    assert event.model == "gpt-6.1-sol"
    assert event.effort == "medium"
    assert event.metadata["route"] == "build"


def test_execution_event_ledger_is_append_only(tmp_path):
    ledger = ExecutionEventLedger(tmp_path)

    ledger.append(
        project_name="demo",
        task_id="TASK-001",
        event_type="primary.started",
        phase="primary",
        status="running",
    )

    ledger.append(
        project_name="demo",
        task_id="TASK-001",
        event_type="primary.completed",
        phase="primary",
        status="success",
    )

    path = (
        tmp_path
        / "demo"
        / "events.jsonl"
    )

    rows = path.read_text(
        encoding="utf-8"
    ).splitlines()

    assert len(rows) == 2

    first = json.loads(rows[0])
    second = json.loads(rows[1])

    assert first["event_type"] == "primary.started"
    assert second["event_type"] == "primary.completed"


def test_missing_execution_event_ledger_returns_empty(tmp_path):
    ledger = ExecutionEventLedger(tmp_path)

    assert ledger.read("missing") == []
