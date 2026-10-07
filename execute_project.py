import json
from pathlib import Path

from app.execution.engine import ExecutionEngine
from app.execution.storage import ExecutionStorage
from app.routing.engine import RoutingEngine
from route_project import resolve_project_path


YES = {"y", "yes", "iya", "ya"}


def main():
    print("=== AI Agency Execution Layer V0.7 ===")

    raw = input(
        "\nMasukkan project hasil V0.4/V0.5.\n"
        "Contoh: data-eng-port\n> "
    ).strip()

    if not raw:
        print("✗ Project wajib diisi.")
        return

    try:
        project_root = resolve_project_path(raw)
    except FileNotFoundError as exc:
        print(f"\n✗ {exc}")
        return

    print("\n✓ Project ditemukan:")
    print(project_root)

    plan = RoutingEngine().build_plan(project_root)

    mode = input(
        "\nMode execution:\n"
        "1. Dry-run (aman, tidak menjalankan Claude/Codex)\n"
        "2. Execute real CLI\n"
        "Pilih [1/2]: "
    ).strip()

    dry_run = mode != "2"

    if not dry_run:
        import shutil

        engine = ExecutionEngine()
        missing = [
            binary for binary in sorted(engine.required_binaries(plan))
            if shutil.which(binary) is None
        ]

        if missing:
            print("\n✗ Real execution belum bisa dimulai.")
            print("CLI berikut belum tersedia di PATH:")
            for binary in missing:
                print(f"- {binary}")
            print("\nPastikan Claude Code, Codex, dan Git tersedia sebelum real execution.")
            return

        print("\nPreflight CLI: OK")
        print("- git")
        if any(d.primary_owner == "claude_code" for d in plan.decisions):
            print("- claude")
        if any(d.primary_owner == "codex" for d in plan.decisions):
            print("- codex")

        print("\nWorkflow real execution:")
        print("integration branch -> task branch -> execute -> commit -> merge ke integration")
        print("Branch main/master tidak akan disentuh otomatis.")

        confirm = input(
            "\n⚠ Mode real akan menjalankan Claude Code/Codex CLI dan dapat mengubah file project.\n"
            "Lanjut? [y/n]: "
        ).strip().lower()

        if confirm not in YES:
            print("✗ Execution dibatalkan.")
            return

    report = ExecutionEngine().execute(
        plan,
        project_root,
        dry_run=dry_run,
        allow_escalation=True,
    )

    print("\n========================================================================")
    print("EXECUTION REPORT")
    print("========================================================================")
    for record in report.records:
        print(f"{record.task_id}: {record.owner} -> {record.status}")
        print(f"  branch : {record.branch}")
        if record.command_preview:
            print(f"  command: {record.command_preview}")
        if record.escalated:
            print(f"  escalated -> {record.escalation_owner}")
        if record.qa_profile:
            print(f"  QA profile: {record.qa_profile}")
        if record.repair_attempted:
            state = "success" if record.repair_succeeded else "failed"
            print(f"  QA repair: {state} via {record.repair_owner}")
            if record.repair_branch:
                print(f"  repair branch: {record.repair_branch}")
        if record.stderr and record.status in {"failed", "skipped"}:
            print(f"  error  : {record.stderr.strip()[:300]}")

    saved = ExecutionStorage().save(report, Path("runtime_data"))
    print("\n✓ Execution report disimpan di luar project repo:")
    print(saved.resolve())


if __name__ == "__main__":
    main()
