from pathlib import Path

from app.deployment.executor import DeploymentExecutor
from app.deployment.guard import (
    DeploymentGuard,
    DeploymentGuardError,
)
from app.deployment.handoff import HandoffBuilder
from app.deployment.planner import DeploymentPlanner
from app.workspace import (
    resolve_project,
    delivery_report_path,
)


def main():
    print("=== AI Agency Deployment & Handoff Layer ===")

    name = input("Project name: ").strip()

    if not name:
        print("Project name wajib diisi.")
        return

    repo = resolve_project(name)

    if not repo:
        print(f"Project `{name}` tidak ditemukan.")
        return

    report_path = delivery_report_path(name)

    try:
        delivery_report = DeploymentGuard(
            report_path,
            repo,
        ).validate()

    except DeploymentGuardError as exc:
        print(f"\nBLOCKED: {exc}")
        print(f"Expected delivery report: {report_path}")
        return

    print(
        "\nMode:\n"
        "1. Dry-run deployment plan\n"
        "2. Execute deployment"
    )

    choice = input("Pilih [1/2]: ").strip()

    mode = (
        "execute"
        if choice == "2"
        else "dry-run"
    )

    plan = DeploymentPlanner(repo).create_plan(
        project_name=name,
        mode=mode,
    )

    runtime = (
        Path(__file__).resolve().parent
        / "runtime_data"
        / "deployment"
        / name
    )

    runtime.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        runtime / "deployment_plan.json"
    ).write_text(
        plan.model_dump_json(indent=2),
        encoding="utf-8",
    )

    print(
        "\n"
        + "=" * 72
        + "\nDEPLOYMENT PLAN\n"
        + "=" * 72
    )

    print(
        f"Provider : {plan.provider}\n"
        f"Branch   : {plan.source_branch}\n"
        f"Commit   : {plan.commit_sha}\n"
        f"Mode     : {plan.mode}\n"
        f"Status   : {plan.status}"
    )

    if plan.blockers:
        print("\nBlockers:")

        for blocker in plan.blockers:
            print(f"- {blocker}")

    if plan.commands:
        print("\nCommands:")

        for step in plan.commands:
            print(
                f"- {step.label}: "
                f"{' '.join(step.command)}"
            )

    if plan.status != "ready":
        print("\nDeployment tidak dijalankan.")
        return

    result = None

    if mode == "execute":
        print(
            "\nWARNING: this will run a remote "
            "production deployment command."
        )

        approved = (
            input(
                "Type DEPLOY to approve: "
            ).strip()
            == "DEPLOY"
        )

        if not approved:
            print("Deployment dibatalkan.")
            return

        result = DeploymentExecutor(repo).execute(
            plan,
            approved=True,
        )

        (
            runtime / "deployment_result.json"
        ).write_text(
            result.model_dump_json(indent=2),
            encoding="utf-8",
        )

        print(
            f"\nDeployment result: {result.status}"
        )

        if result.deployment_url:
            print(
                f"URL: {result.deployment_url}"
            )

        if result.status != "deployed":
            print(
                "Deployment tidak berhasil; "
                "handoff deployment final tidak dibuat."
            )
            return

    handoff_dir = (
        Path(__file__).resolve().parent
        / "runtime_data"
        / "handoff"
        / name
    )

    HandoffBuilder(repo).build(
        plan=plan,
        result=result,
        delivery_report=delivery_report,
        output_dir=handoff_dir,
    )

    print("\nHandoff report:")
    print(
        handoff_dir / "handoff_report.json"
    )
    print(
        handoff_dir / "handoff_report.md"
    )


if __name__ == "__main__":
    main()
