from __future__ import annotations

from pathlib import Path


SYSTEM_ROOT = Path(__file__).resolve().parents[1]
SPEC_ROOT = SYSTEM_ROOT.parent
OUTPUT_ROOT = SPEC_ROOT / "AI_Output"


def ensure_output_root() -> Path:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    return OUTPUT_ROOT


def project_path(name: str) -> Path:
    clean_name = name.strip()

    if not clean_name:
        raise ValueError("Project name wajib diisi.")

    return ensure_output_root() / clean_name


def resolve_project(raw: str) -> Path | None:
    value = raw.strip()

    if not value:
        return None

    candidate = Path(value).expanduser()

    # Absolute/existing path remains supported.
    if candidate.exists():
        return candidate.resolve()

    # Canonical AI Agency output workspace.
    canonical = OUTPUT_ROOT / value

    if canonical.exists():
        return canonical.resolve()

    return None


def delivery_report_path(name: str) -> Path:
    return (
        SYSTEM_ROOT
        / "runtime_data"
        / "delivery"
        / name
        / "delivery_report.json"
    )
