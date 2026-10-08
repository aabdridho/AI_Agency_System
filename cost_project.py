from pathlib import Path

from app.execution.costs import write_project_cost_summary


def main():
    print("=== AI Agency Cost Engine ===")
    print()
    print("Masukkan nama project:")
    project_name = input("> ").strip()

    if not project_name:
        raise SystemExit("Project tidak boleh kosong.")

    root = Path("runtime_data") / "usage"

    usage_file = (
        root
        / project_name
        / "usage.jsonl"
    )

    if not usage_file.exists():
        raise SystemExit(
            f"Usage ledger tidak ditemukan: {usage_file}"
        )

    summary = write_project_cost_summary(
        root,
        project_name,
    )

    print()
    print("=" * 72)
    print("COST SUMMARY")
    print("=" * 72)
    print(f"Project               : {summary.project_name}")
    print(f"Usage records         : {summary.total_records}")
    print(f"Priced records        : {summary.priced_records}")
    print(f"Unknown cost records  : {summary.unknown_records}")
    print(
        "Equivalent list cost  : "
        f"${summary.known_equivalent_cost_usd}"
    )
    print(
        "Actual cash cost      : "
        "UNKNOWN (not inferred from list pricing)"
    )
    print(f"Complete              : {summary.is_complete}")

    print()
    print("Per record:")

    for r in summary.records:
        cost = (
            f"${r.equivalent_cost_usd}"
            if r.equivalent_cost_usd is not None
            else "UNKNOWN"
        )

        print(
            f"- {r.task_id} | {r.phase} | "
            f"{r.model or 'unknown-model'} | "
            f"{r.goat_tier or '-'} | "
            f"{cost} | {r.cost_basis}"
        )

        if r.reason:
            print(f"  reason: {r.reason}")

    path = (
        root
        / project_name
        / "cost_summary.json"
    )

    print()
    print(f"Saved: {path}")


if __name__ == "__main__":
    main()
