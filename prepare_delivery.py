from pathlib import Path

from app.delivery.engine import DeliveryEngine
from app.delivery.resolver import InternalResolver, InternalResolutionError
from app.workspace import resolve_project


def print_report(report):
    print()
    print("=" * 72)
    print("DELIVERY READINESS REPORT")
    print("=" * 72)

    for check in report.checks:
        owner = f" [{check.blocker_class}]" if check.blocker_class else ""
        print(
            f"{check.status.upper():7} "
            f"{check.check_id}{owner}: {check.detail}"
        )
        if check.proposed_resolution:
            print(f"         proposed: {check.proposed_resolution}")

    print()
    print("Blocker ownership:")
    for key in (
        "AUTO_RESOLVABLE_INTERNAL",
        "CLIENT_INPUT_REQUIRED",
        "HARD_TECHNICAL_BLOCKER",
    ):
        print(f"- {key}: {report.blocker_summary.get(key, 0)}")

    print()
    print(f"Overall: {report.overall_status.upper()}")

    if report.client_input_request:
        print()
        print("Client input request:")
        print(report.client_input_request)


def main():
    print("=== AI Agency Delivery Layer ===")
    print()
    print("Masukkan project yang akan dicek kesiapan delivery.")
    name = input("> ").strip()

    if not name:
        print("Project name wajib diisi.")
        return

    repo = resolve_project(name)
    if not repo:
        print(f"Project `{name}` tidak ditemukan.")
        return

    print()
    print("✓ Project ditemukan:")
    print(repo)
    print()
    print(
        "Delivery readiness akan menjalankan validation/build "
        "dan TIDAK melakukan deploy."
    )

    if input("Lanjut? [y/n]: ").strip().lower() != "y":
        print("Dibatalkan.")
        return

    runtime = Path(__file__).resolve().parent / "runtime_data" / "delivery"
    engine = DeliveryEngine()

    report = engine.run(
        project_name=name,
        project_root=repo,
        output_root=runtime,
        run_production_validation=True,
    )
    print_report(report)

    auto = [
        c
        for c in report.checks
        if c.status == "blocker"
        and c.blocker_class == "AUTO_RESOLVABLE_INTERNAL"
        and c.auto_resolvable
    ]

    if auto:
        print()
        print("Safe internal resolution tersedia:")
        for check in auto:
            print(f"- {check.title}: {check.proposed_resolution}")

        if (
            input(
                "\nTerapkan safe internal resolution lalu cek ulang? [y/n]: "
            ).strip().lower()
            == "y"
        ):
            try:
                result = (
                    InternalResolver(repo)
                    .resolve_nextjs_deployment_target_to_vercel()
                )
                print()
                print("✓ Internal resolution diterapkan dan di-commit:")
                print(f"  {result['resolution']}")
                for path in result["changed_files"]:
                    print(f"  - {path}")

                print()
                print("Menjalankan delivery readiness ulang...")

                report = engine.run(
                    project_name=name,
                    project_root=repo,
                    output_root=runtime,
                    run_production_validation=True,
                )
                print_report(report)

            except InternalResolutionError as exc:
                print()
                print(f"✗ Safe internal resolution dibatalkan: {exc}")

    print()
    print("Report:")
    print(runtime / name / "delivery_report.json")
    print(runtime / name / "delivery_report.md")

    if report.client_input_request:
        print()
        print("Client input request packet:")
        print(report.client_input_request)


if __name__ == "__main__":
    main()
