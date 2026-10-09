import json

from app.execution.costs import load_usage_records
from app.execution.usage import UsageLedger, UsageMetrics


def _metrics():
    return UsageMetrics(
        provider="openai",
        model="gpt-6.1-sol",
        input_tokens=100,
        output_tokens=10,
    )


def test_usage_rows_receive_unique_identity(tmp_path):
    ledger = UsageLedger(
        tmp_path / "usage"
    )

    path = ledger.append(
        project_name="demo",
        task_id="TASK-001",
        owner="codex",
        phase="implementation",
        run_id="run-a",
        metrics=_metrics(),
    )

    ledger.append(
        project_name="demo",
        task_id="TASK-001",
        owner="codex",
        phase="implementation",
        run_id="run-a",
        metrics=_metrics(),
    )

    rows = load_usage_records(path)

    assert len(rows) == 2

    assert rows[0].usage_id
    assert rows[1].usage_id
    assert (
        rows[0].usage_id
        != rows[1].usage_id
    )


def test_legacy_usage_without_usage_id_remains_readable(
    tmp_path,
):
    path = (
        tmp_path
        / "usage"
        / "demo"
        / "usage.jsonl"
    )

    path.parent.mkdir(parents=True)

    path.write_text(
        json.dumps(
            {
                "timestamp": "2026-10-09T00:00:00Z",
                "project_name": "demo",
                "task_id": "TASK-001",
                "owner": "codex",
                "phase": "implementation",
                "run_id": None,
                "attempt": 1,
                "metrics": {
                    "provider": "openai",
                    "model": "gpt-6.1-sol",
                    "input_tokens": 100,
                    "output_tokens": 10,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    rows = load_usage_records(path)

    assert len(rows) == 1
    assert rows[0].usage_id is None
