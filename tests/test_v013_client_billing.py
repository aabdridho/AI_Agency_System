import json
from decimal import Decimal

import pytest

from app.execution.billing import (
    BillingConfig,
    BillingEngine,
    BillingPolicy,
    write_project_billing_summary,
)
from app.execution.costs import ProjectCostSummary


def cost_summary(
    *,
    equivalent="1.000000000",
    complete=True,
):
    return ProjectCostSummary(
        project_name="demo",
        total_records=1,
        priced_records=1 if complete else 0,
        unknown_records=0 if complete else 1,
        known_equivalent_cost_usd=equivalent,
        actual_cash_cost_usd=None,
        is_complete=complete,
        records=[],
    )


def test_basic_billing_formula():
    policy = BillingPolicy(
        infrastructure_allocation_usd="1",
        subscription_allocation_usd="2",
        engineering_service_fee_usd="6",
        qa_risk_overhead_percent="10",
        margin_percent="20",
    )

    result = BillingEngine().calculate(
        cost_summary(),
        policy,
    )

    # base = 1 AI + 1 infra + 2 sub + 6 eng = 10
    # QA = 1
    # pre-margin = 11
    # margin = 2.2
    # total = 13.2
    assert (
        Decimal(result.final_client_price_usd)
        == Decimal("13.2")
    )


def test_minimum_project_fee_applies():
    policy = BillingPolicy(
        minimum_project_fee_usd="50"
    )

    result = BillingEngine().calculate(
        cost_summary(equivalent="0.01"),
        policy,
    )

    assert (
        Decimal(result.final_client_price_usd)
        == Decimal("50")
    )


def test_actual_provider_cost_remains_unknown():
    result = BillingEngine().calculate(
        cost_summary(),
        BillingPolicy(),
    )

    assert (
        result.actual_provider_cash_cost_usd
        is None
    )

    assert (
        result.actual_provider_cost_known
        is False
    )


def test_incomplete_ai_cost_marks_billing_incomplete():
    result = BillingEngine().calculate(
        cost_summary(
            equivalent="0",
            complete=False,
        ),
        BillingPolicy(),
    )

    assert result.ai_cost_complete is False
    assert result.billing_complete is False


def test_negative_values_rejected():
    with pytest.raises(ValueError):
        BillingEngine().calculate(
            cost_summary(),
            BillingPolicy(
                margin_percent="-1"
            ),
        )


def test_billing_config_roundtrip(tmp_path):
    path = tmp_path / "billing.json"

    config = BillingConfig(path)

    policy = BillingPolicy(
        engineering_service_fee_usd="25",
        margin_percent="15",
    )

    config.save(policy)

    loaded = config.load()

    assert (
        loaded.engineering_service_fee_usd
        == "25"
    )

    assert loaded.margin_percent == "15"


def test_project_billing_summary_written(tmp_path):
    usage_root = tmp_path / "usage"

    project = usage_root / "demo"
    project.mkdir(parents=True)

    summary = cost_summary()

    (
        project / "cost_summary.json"
    ).write_text(
        summary.model_dump_json(indent=2),
        encoding="utf-8",
    )

    policy = BillingPolicy(
        engineering_service_fee_usd="10"
    )

    result = write_project_billing_summary(
        usage_root,
        "demo",
        policy=policy,
    )

    assert (
        project / "billing_summary.json"
    ).exists()

    assert (
        Decimal(result.final_client_price_usd)
        == Decimal("11")
    )
