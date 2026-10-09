import json

from app.execution.events import ExecutionEventLedger
from app.execution.models import ExecutionReport
from app.execution.storage import ExecutionStorage
from app.execution.usage import UsageLedger, UsageMetrics


def test_execution_event_run_identity_and_sequence(tmp_path):
    ledger = ExecutionEventLedger(
        tmp_path / "execution"
    )

    ledger.append(
        project_name="demo",
        task_id="TASK-001",
        event_type="task.created",
        phase="task",
        run_id="run-a",
    )

    ledger.append(
        project_name="demo",
        task_id="TASK-001",
        event_type="triage.completed",
        phase="triage",
        run_id="run-a",
        status="success",
    )

    rows = ledger.read("demo")

    assert len(rows) == 2

    assert rows[0].run_id == "run-a"
    assert rows[1].run_id == "run-a"

    assert rows[0].event_id
    assert rows[1].event_id
    assert rows[0].event_id != rows[1].event_id

    assert rows[0].sequence == 1
    assert rows[1].sequence == 2


def test_execution_event_sequence_continues_after_reopen(tmp_path):
    root = tmp_path / "execution"

    first = ExecutionEventLedger(root)

    first.append(
        project_name="demo",
        event_type="task.created",
        phase="task",
        run_id="run-a",
    )

    second = ExecutionEventLedger(root)

    second.append(
        project_name="demo",
        event_type="report.completed",
        phase="report",
        run_id="run-a",
        status="success",
    )

    rows = second.read("demo")

    assert rows[-1].sequence == 2


def test_legacy_execution_event_remains_readable(tmp_path):
    path = (
        tmp_path
        / "execution"
        / "demo"
        / "events.jsonl"
    )

    path.parent.mkdir(parents=True)

    path.write_text(
        json.dumps(
            {
                "timestamp": "2026-10-09T00:00:00Z",
                "project_name": "demo",
                "task_id": "TASK-001",
                "event_type": "task.created",
                "phase": "task",
                "status": "info",
                "owner": None,
                "model": None,
                "effort": None,
                "attempt": 1,
                "detail": None,
                "metadata": {},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    row = ExecutionEventLedger(
        tmp_path / "execution"
    ).read("demo")[0]

    assert row.run_id is None
    assert row.event_id is None
    assert row.sequence is None


def test_usage_record_has_run_and_attempt(tmp_path):
    ledger = UsageLedger(
        tmp_path / "usage"
    )

    path = ledger.append(
        project_name="demo",
        task_id="TASK-001",
        owner="codex",
        phase="qa-repair-2",
        run_id="run-a",
        attempt=2,
        metrics=UsageMetrics(
            provider="openai",
            model="gpt-6.1-sol",
        ),
    )

    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        ).splitlines()[0]
    )

    assert payload["run_id"] == "run-a"
    assert payload["attempt"] == 2


def test_execution_storage_keeps_latest_and_run_history(tmp_path):
    report = ExecutionReport(
        project_name="demo",
        dry_run=False,
        records=[],
        run_id="run-a",
    )

    latest = ExecutionStorage().save(
        report,
        tmp_path,
    )

    historical = (
        tmp_path
        / "execution"
        / "demo"
        / "runs"
        / "run-a"
        / "execution_report.json"
    )

    assert latest.is_file()
    assert historical.is_file()

    latest_data = json.loads(
        latest.read_text(
            encoding="utf-8"
        )
    )

    historical_data = json.loads(
        historical.read_text(
            encoding="utf-8"
        )
    )

    assert latest_data["run_id"] == "run-a"
    assert historical_data["run_id"] == "run-a"
