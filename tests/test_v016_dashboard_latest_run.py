import json
from datetime import datetime, timezone

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


def _usage_row(run_id, task_id, input_tokens):
    return {
        "timestamp": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
        "project_name": "demo",
        "task_id": task_id,
        "owner": "codex",
        "phase": "implementation",
        "run_id": run_id,
        "attempt": 1,
        "metrics": {
            "provider": "openai",
            "model": "gpt-6.1-sol",
            "input_tokens": input_tokens,
            "cached_input_tokens": 0,
            "cache_write_input_tokens": 0,
            "output_tokens": 10,
            "reasoning_output_tokens": 0,
            "requested_effort": "medium",
            "goat_tier": "build",
        },
    }


def test_project_detail_filters_events_and_usage_to_latest_run(
    tmp_path,
):
    runtime_root = (
        tmp_path
        / "runtime_data"
    )

    output_root = (
        tmp_path
        / "output"
    )

    (
        output_root
        / "demo"
    ).mkdir(parents=True)

    _write_json(
        runtime_root
        / "execution"
        / "demo"
        / "execution_report.json",
        {
            "project_name": "demo",
            "dry_run": False,
            "records": [],
            "run_id": "run-b",
            "policy_version": "0.6",
        },
    )

    _write_jsonl(
        runtime_root
        / "execution"
        / "demo"
        / "events.jsonl",
        [
            {
                "timestamp": "2026-10-09T00:00:00+00:00",
                "project_name": "demo",
                "task_id": "TASK-001",
                "run_id": "run-a",
                "event_id": "event-a",
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
            },
            {
                "timestamp": "2026-10-09T00:01:00+00:00",
                "project_name": "demo",
                "task_id": "TASK-002",
                "run_id": "run-b",
                "event_id": "event-b",
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
            },
        ],
    )

    _write_jsonl(
        runtime_root
        / "usage"
        / "demo"
        / "usage.jsonl",
        [
            _usage_row(
                "run-a",
                "TASK-001",
                100,
            ),
            _usage_row(
                "run-b",
                "TASK-002",
                200,
            ),
        ],
    )

    svc = DashboardService(
        runtime_root=runtime_root,
        output_root=output_root,
    )

    detail = svc.detail("demo")

    assert (
        detail.execution_run_id
        == "run-b"
    )

    assert detail.execution_events is not None
    assert len(detail.execution_events) == 1
    assert (
        detail.execution_events[0]["run_id"]
        == "run-b"
    )

    assert detail.usage_records is not None
    assert len(detail.usage_records) == 1
    assert (
        detail.usage_records[0]["run_id"]
        == "run-b"
    )

    assert (
        detail.usage_records[0]
        ["task_id"]
        == "TASK-002"
    )


def test_project_detail_legacy_execution_keeps_legacy_rows(
    tmp_path,
):
    runtime_root = (
        tmp_path
        / "runtime_data"
    )

    output_root = (
        tmp_path
        / "output"
    )

    (
        output_root
        / "demo"
    ).mkdir(parents=True)

    _write_json(
        runtime_root
        / "execution"
        / "demo"
        / "execution_report.json",
        {
            "project_name": "demo",
            "dry_run": False,
            "records": [],
            "policy_version": "0.6",
        },
    )

    _write_jsonl(
        runtime_root
        / "execution"
        / "demo"
        / "events.jsonl",
        [
            {
                "timestamp": "2026-10-09T00:00:00+00:00",
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
        ],
    )

    _write_jsonl(
        runtime_root
        / "usage"
        / "demo"
        / "usage.jsonl",
        [
            _usage_row(
                None,
                "TASK-001",
                100,
            )
        ],
    )

    svc = DashboardService(
        runtime_root=runtime_root,
        output_root=output_root,
    )

    detail = svc.detail("demo")

    assert (
        detail.execution_run_id
        is None
    )

    assert detail.execution_events is not None
    assert len(detail.execution_events) == 1

    assert detail.usage_records is not None
    assert len(detail.usage_records) == 1


def test_latest_run_does_not_include_legacy_rows(
    tmp_path,
):
    runtime_root = (
        tmp_path
        / "runtime_data"
    )

    output_root = (
        tmp_path
        / "output"
    )

    (
        output_root
        / "demo"
    ).mkdir(parents=True)

    _write_json(
        runtime_root
        / "execution"
        / "demo"
        / "execution_report.json",
        {
            "project_name": "demo",
            "dry_run": False,
            "records": [],
            "run_id": "run-new",
            "policy_version": "0.6",
        },
    )

    _write_jsonl(
        runtime_root
        / "execution"
        / "demo"
        / "events.jsonl",
        [
            {
                "timestamp": "2026-10-08T00:00:00+00:00",
                "project_name": "demo",
                "task_id": "TASK-OLD",
                "event_type": "task.created",
                "phase": "task",
                "status": "info",
                "owner": None,
                "model": None,
                "effort": None,
                "attempt": 1,
                "detail": None,
                "metadata": {},
            },
            {
                "timestamp": "2026-10-09T00:00:00+00:00",
                "project_name": "demo",
                "task_id": "TASK-NEW",
                "run_id": "run-new",
                "event_id": "new-1",
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
            },
        ],
    )

    svc = DashboardService(
        runtime_root=runtime_root,
        output_root=output_root,
    )

    detail = svc.detail("demo")

    assert len(
        detail.execution_events
        or []
    ) == 1

    assert (
        detail.execution_events[0]
        ["task_id"]
        == "TASK-NEW"
    )
