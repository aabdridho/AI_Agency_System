import pytest

from app.orchestration.models import (
    OrchestrationState,
)
from app.orchestration.orchestrator import (
    ProjectOrchestrator,
)


def _orchestrator(tmp_path):
    runtime = tmp_path / "runtime_data"
    output = tmp_path / "AI_Output"

    (output / "demo").mkdir(
        parents=True,
        exist_ok=True,
    )

    return ProjectOrchestrator(
        runtime_root=runtime,
        output_root=output,
    )


def _waiting():
    return OrchestrationState(
        project_name="demo",
        status="waiting_approval",
        current_stage="execution",
        completed_stages=[
            "discovery",
            "documentation",
            "routing",
        ],
        waiting_for=(
            "real_execution_approval"
        ),
    )


def test_execution_lock_rejects_duplicate_run(
    tmp_path,
):
    first = _orchestrator(tmp_path)
    second = _orchestrator(tmp_path)

    lock = first._acquire_execution_lock(
        "demo"
    )

    try:
        with pytest.raises(
            RuntimeError,
            match="Duplicate execution ditolak",
        ):
            second.run_until_blocked(
                "demo",
                approve_real_execution=True,
            )
    finally:
        first._release_execution_lock(
            lock
        )


def test_execution_state_is_running_before_engine(
    tmp_path,
    monkeypatch,
):
    orchestrator = _orchestrator(tmp_path)

    waiting = _waiting()

    monkeypatch.setattr(
        orchestrator,
        "resume",
        lambda project_name: waiting,
    )

    observed = {}

    def fake_execution(project_name):
        persisted = (
            orchestrator.state_store.load(
                project_name
            )
        )

        observed["status"] = (
            persisted.status
        )

        observed["stage"] = (
            persisted.current_stage
        )

        observed["waiting_for"] = (
            persisted.waiting_for
        )

        return OrchestrationState(
            project_name=project_name,
            status="failed",
            current_stage="execution",
            completed_stages=list(
                waiting.completed_stages
            ),
            failed_stage="execution",
            last_error="test-stop",
        )

    monkeypatch.setattr(
        orchestrator,
        "run_execution",
        fake_execution,
    )

    result = orchestrator.run_until_blocked(
        "demo",
        approve_real_execution=True,
    )

    assert observed["status"] == "running"
    assert observed["stage"] == "execution"
    assert observed["waiting_for"] is None

    assert result.status == "failed"

    assert not (
        orchestrator._execution_lock_path(
            "demo"
        ).exists()
    )


def test_execution_lock_released_after_failure(
    tmp_path,
    monkeypatch,
):
    orchestrator = _orchestrator(tmp_path)

    monkeypatch.setattr(
        orchestrator,
        "resume",
        lambda project_name: _waiting(),
    )

    def explode(project_name):
        raise RuntimeError(
            "engine exploded"
        )

    monkeypatch.setattr(
        orchestrator,
        "run_execution",
        explode,
    )

    with pytest.raises(
        RuntimeError,
        match="engine exploded",
    ):
        orchestrator.run_until_blocked(
            "demo",
            approve_real_execution=True,
        )

    assert not (
        orchestrator._execution_lock_path(
            "demo"
        ).exists()
    )

    persisted = (
        orchestrator.state_store.load(
            "demo"
        )
    )

    assert persisted is not None
    assert persisted.status == "failed"
    assert (
        persisted.current_stage
        == "execution"
    )
    assert (
        persisted.failed_stage
        == "execution"
    )


def test_non_approved_inspection_does_not_create_lock(
    tmp_path,
    monkeypatch,
):
    orchestrator = _orchestrator(tmp_path)

    waiting = _waiting()

    monkeypatch.setattr(
        orchestrator,
        "resume",
        lambda project_name: waiting,
    )

    result = orchestrator.run_until_blocked(
        "demo",
        approve_real_execution=False,
    )

    assert result.status == "waiting_approval"

    assert not (
        orchestrator._execution_lock_path(
            "demo"
        ).exists()
    )
