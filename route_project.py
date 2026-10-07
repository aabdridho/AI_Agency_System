from pathlib import Path

from app.routing.engine import RoutingEngine
from app.routing.storage import RoutingStorage
from app.routing.summary import RoutingSummary
from app.workspace import resolve_project


def resolve_project_path(raw: str) -> Path:
    project = resolve_project(raw)

    if project:
        return project

    raise FileNotFoundError(
        "Project folder tidak ditemukan.\n"
        f"Input: {raw}\n\n"
        "Gunakan nama project di AI_Output "
        "atau masukkan absolute path."
    )


def main():
    print("=== AI Agency Routing Engine ===")

    project_input = input(
        "\nMasukkan project.\n"
        "Bisa berupa nama project atau absolute path.\n"
        "Contoh: data-eng-port\n> "
    ).strip()

    if not project_input:
        print("Path project wajib diisi.")
        return

    try:
        project_root = resolve_project_path(project_input)
        task_file = project_root / "docs" / "task.md"

        if not task_file.exists():
            print(
                "\nProject ditemukan, "
                "tapi docs/task.md tidak ada:"
            )
            print(task_file)
            return

        print("\nProject ditemukan:")
        print(project_root)

        plan = RoutingEngine().build_plan(project_root)

    except FileNotFoundError as exc:
        print(f"\n{exc}")
        return

    print("\n" + RoutingSummary().render(plan))

    save = input(
        "Simpan routing plan operasional? [Y/n]: "
    ).strip().lower()

    if save not in {"n", "no", "tidak"}:
        path = RoutingStorage().save(
            plan,
            Path("runtime_data"),
        )

        print(
            "\nRouting plan disimpan "
            "di luar project repo:"
        )
        print(path.resolve())


if __name__ == "__main__":
    main()
