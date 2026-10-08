from pathlib import Path

from app.execution.savings import (
    write_project_savings_summary,
)


def main():
    print("=== AI Agency GOAT Savings Engine ===")
    print()

    project_name = input(
        "Masukkan nama project:\n> "
    ).strip()

    if not project_name:
        raise SystemExit("Project tidak boleh kosong.")

    usage_root = Path("runtime_data") / "usage"

    usage_file = (
        usage_root
        / project_name
        / "usage.jsonl"
    )

    if not usage_file.exists():
        raise SystemExit(
            f"Usage ledger tidak ditemukan: {usage_file}"
        )

    summary = write_project_savings_summary(
        usage_root,
        project_name,
    )

    print()
    print("=" * 72)
    print("GOAT SAVINGS SUMMARY")
    print("=" * 72)

    print(f"Project                : {summary.project_name}")
    print(f"Baseline strategy      : {summary.baseline_strategy}")
    print(f"Baseline tier          : {summary.baseline_tier}")
    print(f"Baseline model         : {summary.baseline_model}")

    print(f"Observed records       : {summary.observed_records}")
    print(f"Comparable records     : {summary.comparable_records}")
    print(f"Unknown records        : {summary.unknown_records}")

    print(
        "GOAT equivalent cost   : "
        f"${summary.goat_known_equivalent_cost_usd}"
    )

    print(
        "Baseline equivalent     : "
        f"${summary.baseline_known_equivalent_cost_usd}"
    )

    print(
        "Estimated savings       : "
        f"${summary.estimated_equivalent_savings_usd}"
    )

    print(
        "Estimated savings %     : "
        f"{summary.estimated_savings_percent or 'UNKNOWN'}%"
    )

    print(f"Complete               : {summary.is_complete}")
    print("Estimated              : True")

    print()
    print("NOTE:")
    print(
        "Savings is a counterfactual list-price estimate using the same "
        "observed token quantities. It is not an actual cash saving."
    )

    print()
    print("Per record:")

    for r in summary.records:
        if r.complete:
            print(
                f"- {r.task_id} | {r.actual_model} -> "
                f"{r.baseline_model} | "
                f"${r.goat_equivalent_cost_usd} -> "
                f"${r.baseline_equivalent_cost_usd} | "
                f"save ${r.estimated_equivalent_savings_usd} "
                f"({r.estimated_savings_percent}%)"
            )
        else:
            print(
                f"- {r.task_id} | UNKNOWN | {r.reason}"
            )

    output = (
        usage_root
        / project_name
        / "savings_summary.json"
    )

    print()
    print(f"Saved: {output}")


if __name__ == "__main__":
    main()
