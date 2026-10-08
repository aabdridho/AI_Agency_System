import pytest

from app.models.schemas import (
    DiscoveryResult,
    RequirementItem,
)
from app.orchestration.orchestrator import (
    ProjectOrchestrator,
)


def _o(tmp_path):
    runtime = (
        tmp_path
        / "runtime_data"
    )

    output = (
        tmp_path
        / "AI_Output"
    )

    output.mkdir()

    return ProjectOrchestrator(
        runtime_root=runtime,
        output_root=output,
    )


def _approved_result():
    return DiscoveryResult(
        project_type="website",
        confirmed=[
            RequirementItem(
                key="required_sections",
                value=["home"],
                status="CONFIRMED",
                source="client",
                blocking=False,
                confidence=1.0,
            )
        ],
        inferred=[],
        proposed=[],
        unknown=[],
        internal_decisions=[],
        questions=[],
        ready_for_final_approval=True,
        client_approved=True,
        ready_for_development=True,
    )


def test_approve_discovery_rejects_blocking_result(
    tmp_path,
):
    o = _o(tmp_path)

    result = _approved_result().model_copy(
        update={
            "client_approved": False,
            "ready_for_development": False,
            "ready_for_final_approval": False,
            "unknown": [
                RequirementItem(
                    key="blocking_requirement",
                    value="client input required",
                    status="UNKNOWN",
                    source="discovery",
                    blocking=True,
                    confidence=0.0,
                )
            ],
        }
    )

    with pytest.raises(ValueError):
        o.approve_discovery(
            result
        )


def test_generate_documentation_creates_approved_baseline(
    tmp_path,
):
    o = _o(tmp_path)

    result = _approved_result()

    generated = (
        o.generate_documentation(
            "demo",
            result,
        )
    )

    root = (
        o.output_root
        / "demo"
    )

    requirement = (
        root
        / "docs"
        / "requirement.md"
    )

    task = (
        root
        / "docs"
        / "task.md"
    )

    assert generated
    assert requirement.is_file()
    assert task.is_file()

    text = requirement.read_text(
        encoding="utf-8"
    )

    assert "CLIENT_APPROVED" in text

    assert (
        "Ready for development: True"
        in text
    )

    state = o.resume("demo")

    assert state.completed_stages[:2] == [
        "discovery",
        "documentation",
    ]

    assert state.current_stage == "routing"


def test_documentation_does_not_silently_overwrite_existing_baseline(
    tmp_path,
):
    o = _o(tmp_path)

    root = (
        o.output_root
        / "demo"
        / "docs"
    )

    root.mkdir(
        parents=True
    )

    requirement = (
        root
        / "requirement.md"
    )

    requirement.write_text(
        "existing baseline",
        encoding="utf-8",
    )

    with pytest.raises(
        FileExistsError
    ):
        o.generate_documentation(
            "demo",
            _approved_result(),
        )

    assert (
        requirement.read_text(
            encoding="utf-8"
        )
        == "existing baseline"
    )
