import json
from decimal import Decimal

from app.execution.savings import (
    GoatSavingsEngine,
    write_project_savings_summary,
)
from app.execution.usage import (
    UsageMetrics,
    UsageRecord,
)
from app.routing.goat_config import GoatConfig


def usage(
    *,
    model="gpt-6-luna",
    input_tokens=47067,
    cached=37120,
    output=318,
):
    return UsageRecord(
        timestamp="2026-10-08T00:00:00Z",
        project_name="demo",
        task_id="TASK-001",
        owner="codex",
        phase="implementation",
        metrics=UsageMetrics(
            provider="openai",
            model=model,
            input_tokens=input_tokens,
            cached_input_tokens=cached,
            cache_write_input_tokens=0,
            output_tokens=output,
            reasoning_output_tokens=32,
            model_source="execution_request",
            requested_effort="low",
            goat_tier="build",
        ),
    )


def config(tmp_path, esc="astra"):
    path = tmp_path / "tiers.json"

    path.write_text(
        json.dumps(
            {
                "tiers": {
                    "esc": {
                        "model": esc,
                        "effort": "high",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    return GoatConfig(path)


def test_luna_vs_astra_savings_positive(tmp_path):
    engine = GoatSavingsEngine(
        goat_config=config(tmp_path)
    )

    summary = engine.summarize(
        "demo",
        [usage()],
    )

    assert summary.is_complete is True
    assert summary.baseline_model == "gpt-6-astra"

    assert Decimal(
        summary.baseline_known_equivalent_cost_usd
    ) > Decimal(
        summary.goat_known_equivalent_cost_usd
    )

    assert Decimal(
        summary.estimated_equivalent_savings_usd
    ) > 0


def test_baseline_preserves_observed_token_quantities(tmp_path):
    engine = GoatSavingsEngine(
        goat_config=config(tmp_path)
    )

    result = engine.calculate_record(
        usage(
            input_tokens=1000000,
            cached=0,
            output=0,
        ),
        "gpt-6-astra",
    )

    assert result.complete is True
    assert (
        Decimal(result.baseline_equivalent_cost_usd)
        == Decimal("10")
    )


def test_savings_percentage_is_counterfactual(tmp_path):
    engine = GoatSavingsEngine(
        goat_config=config(tmp_path)
    )

    summary = engine.summarize(
        "demo",
        [usage()],
    )

    assert summary.estimated is True
    assert summary.estimated_savings_percent is not None


def test_same_baseline_and_actual_model_gives_zero_savings(tmp_path):
    engine = GoatSavingsEngine(
        goat_config=config(tmp_path)
    )

    summary = engine.summarize(
        "demo",
        [
            usage(
                model="gpt-6-astra",
            )
        ],
    )

    assert (
        Decimal(summary.estimated_equivalent_savings_usd)
        == 0
    )


def test_unknown_actual_model_makes_summary_incomplete(tmp_path):
    r = usage(model=None)

    engine = GoatSavingsEngine(
        goat_config=config(tmp_path)
    )

    summary = engine.summarize(
        "demo",
        [r],
    )

    assert summary.is_complete is False
    assert summary.comparable_records == 0
    assert summary.unknown_records == 1


def test_summary_file_written(tmp_path):
    usage_root = tmp_path / "usage"
    project = usage_root / "demo"
    project.mkdir(parents=True)

    r = usage()

    (project / "usage.jsonl").write_text(
        r.model_dump_json() + "\n",
        encoding="utf-8",
    )

    summary = write_project_savings_summary(
        usage_root,
        "demo",
        goat_config=config(tmp_path),
    )

    output = project / "savings_summary.json"

    assert output.exists()
    assert summary.project_name == "demo"
