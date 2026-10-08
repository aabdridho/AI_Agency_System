import json
from decimal import Decimal

from fastapi.testclient import TestClient

import api
from app.dashboard.service import DashboardService
from app.execution.usage import (
    UsageMetrics,
    UsageRecord,
)


def build_service(tmp_path):
    runtime = tmp_path / "runtime_data"
    output = tmp_path / "AI_Output"

    (output / "demo" / "docs").mkdir(
        parents=True
    )

    return DashboardService(
        runtime_root=runtime,
        output_root=output,
    )


def write_usage(svc):
    path = (
        svc.runtime_root
        / "usage"
        / "demo"
        / "usage.jsonl"
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    record = UsageRecord(
        timestamp="2026-10-08T00:00:00Z",
        project_name="demo",
        task_id="TASK-001",
        owner="codex",
        phase="implementation",
        metrics=UsageMetrics(
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
        ),
    )

    path.write_text(
        record.model_dump_json() + "\n",
        encoding="utf-8",
    )


def write_configs(svc):
    cfg = svc.runtime_root / "config"
    cfg.mkdir(parents=True, exist_ok=True)

    (cfg / "tiers.json").write_text(
        json.dumps(
            {
                "tiers": {
                    "esc": {
                        "model": "astra",
                        "effort": "high",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    (cfg / "billing.json").write_text(
        json.dumps(
            {
                "currency": "USD",
                "infrastructure_allocation_usd": "0.50",
                "subscription_allocation_usd": "1.00",
                "engineering_service_fee_usd": "10.00",
                "qa_risk_overhead_percent": "10",
                "margin_percent": "20",
                "minimum_project_fee_usd": "15.00",
                "pricing_basis": (
                    "ai_compute_equivalent_list_reference"
                ),
            }
        ),
        encoding="utf-8",
    )


def test_dashboard_economics_live_derivation(tmp_path):
    svc = build_service(tmp_path)
    write_usage(svc)
    write_configs(svc)

    result = svc.economics("demo")

    assert result["available"] is True

    assert (
        result["cost"]["known_equivalent_cost_usd"]
        == "0.001524900"
    )

    assert (
        result["savings"]["baseline_model"]
        == "gpt-6-astra"
    )

    assert Decimal(
        result["savings"][
            "estimated_equivalent_savings_usd"
        ]
    ) > 0

    assert (
        result["billing"][
            "actual_provider_cash_cost_usd"
        ]
        is None
    )


def test_dashboard_economics_without_usage(tmp_path):
    svc = build_service(tmp_path)

    result = svc.economics("demo")

    assert result["available"] is False
    assert result["cost"] is None
    assert result["billing"] is None


def test_billing_config_roundtrip_through_dashboard(tmp_path):
    svc = build_service(tmp_path)

    from app.execution.billing import BillingPolicy

    saved = svc.save_billing_config(
        BillingPolicy(
            infrastructure_allocation_usd="2",
            margin_percent="15",
        )
    )

    loaded = svc.get_billing_config()

    assert saved["source"] == "saved"
    assert loaded["source"] == "saved"

    assert (
        loaded["infrastructure_allocation_usd"]
        == "2"
    )

    assert loaded["margin_percent"] == "15"


def test_api_economics_endpoint(tmp_path):
    svc = build_service(tmp_path)
    write_usage(svc)
    write_configs(svc)

    api.app.dependency_overrides[
        api.get_dashboard
    ] = lambda: svc

    try:
        client = TestClient(api.app)

        response = client.get(
            "/api/projects/demo/economics"
        )

        assert response.status_code == 200

        payload = response.json()

        assert payload["available"] is True
        assert (
            payload["billing"][
                "actual_provider_cost_known"
            ]
            is False
        )
    finally:
        api.app.dependency_overrides.clear()


def test_api_billing_config_put_get(tmp_path):
    svc = build_service(tmp_path)

    api.app.dependency_overrides[
        api.get_dashboard
    ] = lambda: svc

    try:
        client = TestClient(api.app)

        payload = {
            "currency": "USD",
            "infrastructure_allocation_usd": "3",
            "subscription_allocation_usd": "2",
            "engineering_service_fee_usd": "25",
            "qa_risk_overhead_percent": "5",
            "margin_percent": "20",
            "minimum_project_fee_usd": "50",
            "pricing_basis": (
                "ai_compute_equivalent_list_reference"
            ),
        }

        put = client.put(
            "/api/billing/config",
            json=payload,
        )

        assert put.status_code == 200
        assert put.json()["source"] == "saved"

        get = client.get(
            "/api/billing/config"
        )

        assert get.status_code == 200

        assert (
            get.json()[
                "engineering_service_fee_usd"
            ]
            == "25"
        )
    finally:
        api.app.dependency_overrides.clear()
