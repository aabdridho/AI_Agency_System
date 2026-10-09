import json

from app.dashboard.service import DashboardService


def _write_json(path, payload):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def _write_jsonl(path, rows):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        "".join(
            json.dumps(row) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def _service(tmp_path):
    runtime = tmp_path / "runtime_data"
    output = tmp_path / "AI_Output"

    (output / "demo").mkdir(
        parents=True,
    )

    return (
        DashboardService(
            runtime_root=runtime,
            output_root=output,
        ),
        runtime,
    )


def _event(
    run_id,
    event_type,
    sequence,
    status,
):
    return {
        "timestamp": (
            f"2026-10-10T00:00:0{sequence}+00:00"
        ),
        "project_name": "demo",
        "task_id": None,
        "run_id": run_id,
        "event_id": (
            f"{run_id}-{sequence}"
        ),
        "sequence": sequence,
        "event_type": event_type,
        "phase": "run",
        "status": status,
        "owner": "internal_decision",
        "model": None,
        "effort": None,
        "attempt": 1,
        "detail": None,
        "metadata": {},
    }


def test_aborted_new_run_becomes_dashboard_selected_run(
    tmp_path,
):
    svc, runtime = _service(tmp_path)

    _write_json(
        runtime
        / "execution"
        / "demo"
        / "execution_report.json",
        {
            "project_name": "demo",
            "dry_run": False,
            "records": [],
            "run_id": "run-a",
        },
    )

    _write_jsonl(
        runtime
        / "execution"
        / "demo"
        / "events.jsonl",
        [
            _event(
                "run-a",
                "run.started",
                1,
                "running",
            ),
            _event(
                "run-a",
                "run.completed",
                2,
                "success",
            ),
            _event(
                "run-b",
                "run.started",
                1,
                "running",
            ),
            _event(
                "run-b",
                "run.failed",
                2,
                "failed",
            ),
        ],
    )

    detail = svc.detail("demo")

    assert detail.execution_run_id == "run-b"

    assert detail.execution is None

    assert detail.execution_events is not None
    assert len(detail.execution_events) == 2

    assert {
        row["run_id"]
        for row in detail.execution_events
    } == {"run-b"}

    assert [
        row["event_type"]
        for row in detail.execution_events
    ] == [
        "run.started",
        "run.failed",
    ]


def test_completed_latest_run_keeps_matching_report(
    tmp_path,
):
    svc, runtime = _service(tmp_path)

    _write_json(
        runtime
        / "execution"
        / "demo"
        / "execution_report.json",
        {
            "project_name": "demo",
            "dry_run": False,
            "records": [],
            "run_id": "run-b",
        },
    )

    _write_jsonl(
        runtime
        / "execution"
        / "demo"
        / "events.jsonl",
        [
            _event(
                "run-b",
                "run.started",
                1,
                "running",
            ),
            _event(
                "run-b",
                "run.completed",
                2,
                "success",
            ),
        ],
    )

    detail = svc.detail("demo")

    assert detail.execution_run_id == "run-b"
    assert detail.execution is not None
    assert detail.execution["run_id"] == "run-b"


def test_report_run_is_fallback_without_lifecycle_events(
    tmp_path,
):
    svc, runtime = _service(tmp_path)

    _write_json(
        runtime
        / "execution"
        / "demo"
        / "execution_report.json",
        {
            "project_name": "demo",
            "dry_run": False,
            "records": [],
            "run_id": "run-legacy",
        },
    )

    _write_jsonl(
        runtime
        / "execution"
        / "demo"
        / "events.jsonl",
        [
            {
                "timestamp": (
                    "2026-10-09T00:00:00+00:00"
                ),
                "project_name": "demo",
                "task_id": "TASK-001",
                "run_id": "run-legacy",
                "event_id": "legacy-event",
                "sequence": 1,
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
        ],
    )

    detail = svc.detail("demo")

    assert (
        detail.execution_run_id
        == "run-legacy"
    )

    assert detail.execution is not None

    assert (
        detail.execution["run_id"]
        == "run-legacy"
    )
