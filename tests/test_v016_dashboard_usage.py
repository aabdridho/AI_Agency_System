from app.dashboard.service import DashboardService
from app.execution.usage import UsageLedger, UsageMetrics


def test_project_detail_exposes_usage_records(tmp_path):
    runtime_root = tmp_path / "runtime_data"
    output_root = tmp_path / "output"

    project_root = output_root / "demo"
    project_root.mkdir(parents=True)

    UsageLedger(
        runtime_root / "usage"
    ).append(
        project_name="demo",
        task_id="TASK-001",
        owner="claude_code",
        phase="implementation",
        metrics=UsageMetrics(
            provider="anthropic",
            model="claude-sonnet-5-5",
            input_tokens=120,
            cached_input_tokens=80,
            cache_write_input_tokens=10,
            output_tokens=30,
            reasoning_output_tokens=0,
            requested_effort="medium",
            goat_tier="build",
        ),
    )

    svc = DashboardService(
        runtime_root=runtime_root,
        output_root=output_root,
    )

    detail = svc.detail("demo")

    assert detail.usage_records is not None
    assert len(detail.usage_records) == 1

    row = detail.usage_records[0]

    assert row["project_name"] == "demo"
    assert row["task_id"] == "TASK-001"
    assert row["owner"] == "claude_code"
    assert row["phase"] == "implementation"

    metrics = row["metrics"]

    assert metrics["provider"] == "anthropic"
    assert metrics["model"] == "claude-sonnet-5-5"
    assert metrics["input_tokens"] == 120
    assert metrics["cached_input_tokens"] == 80
    assert metrics["cache_write_input_tokens"] == 10
    assert metrics["output_tokens"] == 30
    assert metrics["requested_effort"] == "medium"
    assert metrics["goat_tier"] == "build"


def test_project_detail_without_usage_returns_none(tmp_path):
    runtime_root = tmp_path / "runtime_data"
    output_root = tmp_path / "output"

    (output_root / "demo").mkdir(parents=True)

    svc = DashboardService(
        runtime_root=runtime_root,
        output_root=output_root,
    )

    detail = svc.detail("demo")

    assert detail.usage_records is None
