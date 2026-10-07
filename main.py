from app.discovery.engine import RequirementDiscoveryEngine
from app.discovery.session import InteractiveConfirmationSession
from app.discovery.summary import FinalSummary
from app.discovery.confirmation import ConfirmationGate
from app.documentation.generator import ProjectDocumentationGenerator
from app.workspace import project_path


YES = {"y", "yes", "iya", "ya"}


def main():
    print("=== AI Agency System - Discovery + Documentation ===")

    prompt = input("\nMasukkan prompt client:\n> ").strip()

    refs_raw = input(
        "\nMasukkan reference URL dipisahkan koma (opsional):\n> "
    ).strip()

    references = [
        x.strip()
        for x in refs_raw.split(",")
        if x.strip()
    ]

    result = RequirementDiscoveryEngine().analyze(
        prompt,
        references,
    )

    print("\n=== INITIAL DISCOVERY ===")
    print(result.model_dump_json(indent=2))

    if not result.ready_for_final_approval or result.proposed:
        result = InteractiveConfirmationSession().run(result)

    print("\n" + FinalSummary().render(result))

    if not result.ready_for_final_approval:
        print("\nMasih ada requirement blocking yang belum selesai.")
        return

    approve = input(
        "\nApakah client menyetujui requirement final di atas? [y/n]: "
    ).strip().lower()

    if approve not in YES:
        print(
            "\nRequirement belum disetujui. "
            "Development tidak boleh dimulai."
        )
        return

    result = ConfirmationGate().approve_final(result)

    print("\nCLIENT APPROVED")
    print("READY FOR DEVELOPMENT")

    generate = input(
        "\nGenerate dokumentasi project sekarang? [Y/n]: "
    ).strip().lower()

    if generate in {"n", "no", "tidak"}:
        return

    project_name = (
        input(
            "Nama folder project "
            "(contoh: data-engineering-portfolio):\n> "
        ).strip()
        or "new-project"
    )

    project_root = project_path(project_name)

    if project_root.exists():
        print("\nFolder project tersebut sudah ada.")
        print(
            "AI Agency tidak akan menimpa baseline "
            "dokumentasi secara diam-diam."
        )

        replacement = input(
            "Masukkan nama folder project baru:\n> "
        ).strip()

        if not replacement:
            print("Generation dibatalkan.")
            return

        project_root = project_path(replacement)

    generated = ProjectDocumentationGenerator().generate(
        result,
        project_root,
    )

    print("\nDokumentasi project berhasil dibuat:")

    for path in generated:
        print(f"- {path.resolve()}")


if __name__ == "__main__":
    main()
