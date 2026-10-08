from decimal import Decimal

from app.execution.costs import (
    CostEngine,
    load_usage_records,
)
from app.execution.usage import (
    UsageMetrics,
    UsageRecord,
)


def record(metrics):
    return UsageRecord(
        timestamp="2026-10-08T00:00:00Z",
        project_name="demo",
        task_id="TASK-001",
        owner="codex",
        phase="implementation",
        metrics=metrics,
    )


def test_openai_luna_cost_uses_uncached_plus_cached():
    r = record(
        UsageMetrics(
            provider="openai",
            model="gpt-6-luna",
            input_tokens=47067,
            cached_input_tokens=37120,
            cache_write_input_tokens=0,
            output_tokens=318,
            reasoning_output_tokens=32,
            model_source="execution_request",
            requested_effort="low",
            goat_tier="build",
        )
    )

    result = CostEngine().calculate(r)

    assert result.complete is True
    assert result.cost_basis == "calculated_standard_list"
    assert result.equivalent_cost_usd is not None


def test_reasoning_tokens_are_not_double_billed():
    base = dict(
        provider="openai",
        model="gpt-6-luna",
        input_tokens=1000,
        cached_input_tokens=0,
        cache_write_input_tokens=0,
        output_tokens=1000,
    )

    a = record(
        UsageMetrics(
            **base,
            reasoning_output_tokens=0,
        )
    )

    b = record(
        UsageMetrics(
            **base,
            reasoning_output_tokens=900,
        )
    )

    ca = CostEngine().calculate(a)
    cb = CostEngine().calculate(b)

    assert (
        ca.equivalent_cost_usd
        == cb.equivalent_cost_usd
    )


def test_cached_input_is_not_double_billed_as_uncached():
    r = record(
        UsageMetrics(
            provider="openai",
            model="gpt-6-luna",
            input_tokens=1000000,
            cached_input_tokens=1000000,
            cache_write_input_tokens=0,
            output_tokens=0,
        )
    )

    result = CostEngine().calculate(r)

    assert result.input_cost_usd == "0E-9"
    assert (
        Decimal(result.cached_input_cost_usd)
        == Decimal("0.01")
    )


def test_provider_reported_list_cost_wins():
    r = record(
        UsageMetrics(
            provider="anthropic",
            model="claude-opus-5-5",
            input_tokens=999999,
            cached_input_tokens=999999,
            cache_write_input_tokens=999999,
            output_tokens=999999,
            provider_reported_cost_usd=0.1409042,
            cost_basis="list",
        )
    )

    result = CostEngine().calculate(r)

    assert result.cost_basis == "provider_reported_list"
    assert (
        Decimal(result.equivalent_cost_usd)
        == Decimal("0.140904200")
    )


def test_unknown_model_is_not_guessed():
    r = record(
        UsageMetrics(
            provider="openai",
            model=None,
            input_tokens=100,
            output_tokens=20,
        )
    )

    result = CostEngine().calculate(r)

    assert result.complete is False
    assert result.equivalent_cost_usd is None
    assert result.cost_basis == "unknown"


def test_unverified_model_is_unknown():
    r = record(
        UsageMetrics(
            provider="openai",
            model="future-mystery-model",
            input_tokens=100,
            output_tokens=20,
        )
    )

    result = CostEngine().calculate(r)

    assert result.complete is False
    assert result.equivalent_cost_usd is None


def test_summary_marks_unknown_records_incomplete():
    known = record(
        UsageMetrics(
            provider="openai",
            model="gpt-6-luna",
            input_tokens=1000,
            output_tokens=100,
        )
    )

    unknown = UsageRecord(
        timestamp="2026-10-08T00:00:01Z",
        project_name="demo",
        task_id="TASK-002",
        owner="codex",
        phase="implementation",
        metrics=UsageMetrics(
            provider="openai",
            model=None,
            input_tokens=100,
            output_tokens=20,
        ),
    )

    summary = CostEngine().summarize(
        "demo",
        [known, unknown],
    )

    assert summary.total_records == 2
    assert summary.priced_records == 1
    assert summary.unknown_records == 1
    assert summary.is_complete is False


def test_usage_jsonl_round_trip(tmp_path):
    path = tmp_path / "usage.jsonl"

    r = record(
        UsageMetrics(
            provider="openai",
            model="gpt-6-luna",
            input_tokens=100,
            output_tokens=10,
        )
    )

    path.write_text(
        r.model_dump_json() + "\n",
        encoding="utf-8",
    )

    loaded = load_usage_records(path)

    assert len(loaded) == 1
    assert loaded[0].metrics.model == "gpt-6-luna"
