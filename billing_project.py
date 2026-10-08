from pathlib import Path

from app.execution.billing import (
    BillingConfig,
    write_project_billing_summary,
)


def main():
    print("=== AI Agency Client Billing Layer ===")
    print()

    project_name = input(
        "Masukkan nama project:\n> "
    ).strip()

    if not project_name:
        raise SystemExit(
            "Project tidak boleh kosong."
        )

    usage_root = (
        Path("runtime_data")
        / "usage"
    )

    cost_file = (
        usage_root
        / project_name
        / "cost_summary.json"
    )

    if not cost_file.exists():
        raise SystemExit(
            "Cost summary belum ada. "
            "Jalankan cost_project.py terlebih dahulu."
        )

    config = BillingConfig()
    policy = config.load()

    print()
    print("Billing policy aktif:")
    print(
        f"- infra allocation     : "
        f"${policy.infrastructure_allocation_usd}"
    )
    print(
        f"- subscription alloc   : "
        f"${policy.subscription_allocation_usd}"
    )
    print(
        f"- engineering fee      : "
        f"${policy.engineering_service_fee_usd}"
    )
    print(
        f"- QA/risk overhead     : "
        f"{policy.qa_risk_overhead_percent}%"
    )
    print(
        f"- margin               : "
        f"{policy.margin_percent}%"
    )
    print(
        f"- minimum project fee  : "
        f"${policy.minimum_project_fee_usd}"
    )

    result = write_project_billing_summary(
        usage_root,
        project_name,
        policy=policy,
    )

    print()
    print("=" * 72)
    print("CLIENT BILLING SUMMARY")
    print("=" * 72)

    print(
        f"Project                 : "
        f"{result.project_name}"
    )

    print(
        "AI compute reference    : "
        f"${result.ai_compute_reference_usd}"
    )

    print(
        "Actual provider cost    : "
        + (
            f"${result.actual_provider_cash_cost_usd}"
            if result.actual_provider_cost_known
            else "UNKNOWN"
        )
    )

    print(
        "Infrastructure          : "
        f"${result.infrastructure_allocation_usd}"
    )

    print(
        "Subscription allocation : "
        f"${result.subscription_allocation_usd}"
    )

    print(
        "Engineering/service     : "
        f"${result.engineering_service_fee_usd}"
    )

    print(
        "QA/risk overhead        : "
        f"${result.qa_risk_overhead_usd}"
    )

    print(
        "Margin                  : "
        f"${result.margin_usd}"
    )

    print(
        "Calculated price        : "
        f"${result.calculated_client_price_usd}"
    )

    print(
        "Minimum project fee     : "
        f"${result.minimum_project_fee_usd}"
    )

    print(
        "FINAL CLIENT PRICE      : "
        f"${result.final_client_price_usd}"
    )

    print()
    print(
        "NOTE: final client price is a commercial "
        "price reference, not actual provider cash cost."
    )

    output = (
        usage_root
        / project_name
        / "billing_summary.json"
    )

    print()
    print(f"Saved: {output}")


if __name__ == "__main__":
    main()
