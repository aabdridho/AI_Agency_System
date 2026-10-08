from app.discovery.session import InteractiveConfirmationSession
from app.discovery.summary import FinalSummary
from app.orchestration import ProjectOrchestrator


YES = {
    "y",
    "yes",
    "iya",
    "ya",
}

NO = {
    "n",
    "no",
    "tidak",
}


def print_state(state):
    print()
    print("=" * 72)
    print("AI AGENCY PROJECT STATE")
    print("=" * 72)

    print(f"Project       : {state.project_name}")
    print(f"Status        : {state.status}")
    print(f"Current stage : {state.current_stage or '-'}")

    completed = (
        ", ".join(state.completed_stages)
        if state.completed_stages
        else "-"
    )

    print(f"Completed     : {completed}")
    print(f"Waiting for   : {state.waiting_for or '-'}")
    print(f"Failed stage  : {state.failed_stage or '-'}")

    if state.last_error:
        print(f"Last error    : {state.last_error}")

    print(f"Updated       : {state.updated_at or '-'}")


def new_project(
    orchestrator: ProjectOrchestrator,
):
    print()
    print("=== NEW CLIENT PROJECT ===")

    project_name = input(
        "Nama project:\n> "
    ).strip()

    if not project_name:
        print("Project name wajib diisi.")
        return None

    root = orchestrator.project_root(
        project_name
    )

    if root.exists():
        print()
        print(
            "Project tersebut sudah ada."
        )
        print(
            "Gunakan RESUME PROJECT agar baseline "
            "existing tidak tertimpa."
        )
        return None

    print()
    print("Masukkan brief client:")
    brief = input("> ").strip()

    if not brief:
        print("Client brief wajib diisi.")
        return None

    print()
    print(
        "Reference URL dipisahkan koma "
        "(Enter jika tidak ada):"
    )

    raw_refs = input("> ").strip()

    references = [
        x.strip()
        for x in raw_refs.split(",")
        if x.strip()
    ]

    print()
    print("Menjalankan requirement discovery...")

    result = orchestrator.analyze_brief(
        brief,
        references,
    )

    print()
    print("=== INITIAL DISCOVERY ===")
    print(
        result.model_dump_json(
            indent=2
        )
    )

    if (
        not result.ready_for_final_approval
        or result.proposed
    ):
        result = (
            InteractiveConfirmationSession()
            .run(result)
        )

    print()
    print(
        FinalSummary().render(
            result
        )
    )

    if not result.ready_for_final_approval:
        print()
        print(
            "Masih ada requirement blocking "
            "yang belum diselesaikan."
        )
        return None

    print()
    approval = input(
        "Apakah client menyetujui requirement final? [y/n]: "
    ).strip().lower()

    if approval not in YES:
        print()
        print(
            "Requirement belum disetujui. "
            "Development tidak dijalankan."
        )
        return None

    try:
        result = orchestrator.approve_discovery(
            result
        )
    except ValueError as exc:
        print()
        print(f"APPROVAL ERROR: {exc}")
        return None

    print()
    print("CLIENT APPROVED")
    print("READY FOR DEVELOPMENT")

    try:
        generated = (
            orchestrator.generate_documentation(
                project_name,
                result,
            )
        )
    except Exception as exc:
        print()
        print(
            f"DOCUMENTATION ERROR: {exc}"
        )
        return None

    print()
    print(
        "Dokumentasi project berhasil dibuat:"
    )

    for path in generated:
        print(f"- {path.resolve()}")

    return project_name


def select_project(
    orchestrator: ProjectOrchestrator,
):
    print()
    print("Mode:")
    print("1. New project")
    print("2. Resume project")

    choice = input(
        "Pilih [1/2]: "
    ).strip()

    if choice == "1":
        return new_project(
            orchestrator
        )

    if choice == "2":
        print()
        print(
            "Masukkan nama project:"
        )

        name = input("> ").strip()

        if not name:
            print(
                "Project name wajib diisi."
            )
            return None

        return name

    print(
        "Pilihan tidak valid."
    )
    return None


def run_operational_pipeline(
    orchestrator,
    project_name,
):
    state = orchestrator.resume(
        project_name
    )

    print_state(state)

    if state.current_stage in {
        "discovery",
        "documentation",
    }:
        print()
        print(
            "Project belum memiliki approved "
            "documentation baseline."
        )
        print(
            "Gunakan mode New Project atau "
            "selesaikan requirement approval terlebih dahulu."
        )
        return state

    if state.status == "idle":
        print()
        print(
            "Melanjutkan safe automatic stages..."
        )

        try:
            state = (
                orchestrator.run_until_blocked(
                    project_name,
                    approve_real_execution=False,
                )
            )
        except Exception as exc:
            print()
            print(
                f"PIPELINE ERROR: {exc}"
            )
            return state

        print_state(state)

    # A persisted delivery waiting_input state may be stale after
    # deterministic delivery rules or internal-resolution policy change.
    # Re-running delivery is safe: it performs validation/resolution only
    # and does not re-run implementation model tasks.
    if (
        state.current_stage == "delivery"
        and state.status == "waiting_input"
    ):
        print()
        print(
            "Memeriksa ulang delivery state secara aman..."
        )

        try:
            state = orchestrator.run_delivery(
                project_name
            )
        except Exception as exc:
            print()
            print(
                f"PIPELINE ERROR: {exc}"
            )
            return state

        print_state(state)

        if state.status == "idle":
            try:
                state = orchestrator.run_until_blocked(
                    project_name,
                    approve_real_execution=False,
                )
            except Exception as exc:
                print()
                print(
                    f"PIPELINE ERROR: {exc}"
                )
                return state

            print_state(state)

    if (
        state.status == "waiting_approval"
        and state.waiting_for
        == "real_execution_approval"
    ):
        missing = (
            orchestrator.execution_preflight(
                project_name
            )
        )

        if missing:
            print()
            print(
                "Real execution belum bisa dimulai."
            )
            print(
                "CLI berikut belum tersedia di PATH:"
            )

            for binary in missing:
                print(f"- {binary}")

            return state

        print()
        print("Preflight CLI: OK")
        print()
        print(
            "Real execution akan menjalankan model CLI "
            "dan dapat mengubah project workspace."
        )
        print(
            "Main/master tidak akan disentuh otomatis."
        )

        approve = input(
            "Lanjut real execution? [y/n]: "
        ).strip().lower()

        if approve not in YES:
            print()
            print(
                "Execution tidak dijalankan. "
                "Project dapat di-resume nanti."
            )
            return state

        try:
            state = (
                orchestrator.run_until_blocked(
                    project_name,
                    approve_real_execution=True,
                )
            )
        except Exception as exc:
            print()
            print(
                f"PIPELINE ERROR: {exc}"
            )
            return state

        print_state(state)

    if (
        state.status == "failed"
        and state.failed_stage == "delivery"
    ):
        print()

        retry = input(
            "Delivery sebelumnya gagal. "
            "Jalankan ulang delivery validation? [y/n]: "
        ).strip().lower()

        if retry in YES:
            try:
                state = (
                    orchestrator.run_delivery(
                        project_name
                    )
                )

                if state.status == "idle":
                    state = (
                        orchestrator.run_until_blocked(
                            project_name,
                            approve_real_execution=False,
                        )
                    )

            except Exception as exc:
                print()
                print(
                    f"PIPELINE ERROR: {exc}"
                )
                return state

            print_state(state)

    print()

    if (
        state.status == "waiting_approval"
        and state.waiting_for
        == "deployment_approval"
    ):
        print(
            "PROJECT READY FOR DEPLOYMENT APPROVAL"
        )
        print(
            "Production deployment tetap membutuhkan "
            "approval eksplisit."
        )

    elif state.status == "waiting_input":
        print(
            "Pipeline berhenti aman karena "
            "membutuhkan input."
        )

    elif state.status == "failed":
        print(
            "Pipeline gagal pada stage "
            f"{state.failed_stage or state.current_stage}."
        )

    elif state.status == "completed":
        print(
            "Project sudah selesai sampai deployment."
        )

    else:
        print(
            "Pipeline berhenti di stage: "
            f"{state.current_stage or '-'}"
        )

    return state


def main():
    print(
        "=== AI Agency V0.14 Project Orchestrator ==="
    )

    orchestrator = ProjectOrchestrator()

    project_name = select_project(
        orchestrator
    )

    if not project_name:
        return

    run_operational_pipeline(
        orchestrator,
        project_name,
    )


if __name__ == "__main__":
    main()
