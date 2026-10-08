import json

from app.orchestration.orchestrator import (
    ProjectOrchestrator,
)


def _stage2_orchestrator(tmp_path):
    runtime = tmp_path / "runtime_data"
    output = tmp_path / "AI_Output"
    output.mkdir()

    return ProjectOrchestrator(
        runtime_root=runtime,
        output_root=output,
    )


def _stage2_project(o, name="demo"):
    root = o.output_root / name
    docs = root / "docs"

    docs.mkdir(
        parents=True
    )

    (
        docs / "requirement.md"
    ).write_text(
        "CLIENT_APPROVED\nReady for development: True\n",
        encoding="utf-8",
    )

    (
        docs / "task.md"
    ).write_text(
        "- [ ] Backend Python implementation\n",
        encoding="utf-8",
    )

    return root


def test_run_routing_persists_plan(
    tmp_path,
):
    o = _stage2_orchestrator(
        tmp_path
    )

    _stage2_project(o)

    state = o.run_routing("demo")

    routing_file = (
        o.runtime_root
        / "routing"
        / "demo"
        / "routing_plan.json"
    )

    assert routing_file.is_file()

    assert state.status == "waiting_approval"
    assert state.current_stage == "execution"

    assert (
        state.waiting_for
        == "real_execution_approval"
    )


def test_run_until_blocked_routes_then_waits_for_execution(
    tmp_path,
):
    o = _stage2_orchestrator(
        tmp_path
    )

    _stage2_project(o)

    state = o.run_until_blocked(
        "demo",
        approve_real_execution=False,
    )

    assert state.status == "waiting_approval"
    assert state.current_stage == "execution"

    assert (
        state.waiting_for
        == "real_execution_approval"
    )


def test_run_until_blocked_does_not_execute_without_approval(
    tmp_path,
    monkeypatch,
):
    o = _stage2_orchestrator(
        tmp_path
    )

    _stage2_project(o)

    called = {
        "execution": False
    }

    def forbidden_execution(name):
        called["execution"] = True
        raise AssertionError(
            "Execution must not run."
        )

    monkeypatch.setattr(
        o,
        "run_execution",
        forbidden_execution,
    )

    state = o.run_until_blocked(
        "demo",
        approve_real_execution=False,
    )

    assert called["execution"] is False

    assert (
        state.waiting_for
        == "real_execution_approval"
    )


def test_run_delivery_uses_runtime_delivery_directory(
    tmp_path,
    monkeypatch,
):
    o = _stage2_orchestrator(
        tmp_path
    )

    root = _stage2_project(o)

    routing = (
        o.runtime_root
        / "routing"
        / "demo"
    )

    routing.mkdir(
        parents=True
    )

    (
        routing / "routing_plan.json"
    ).write_text(
        json.dumps(
            {
                "project_name": "demo",
                "decisions": [],
            }
        ),
        encoding="utf-8",
    )

    execution = (
        o.runtime_root
        / "execution"
        / "demo"
    )

    execution.mkdir(
        parents=True
    )

    (
        execution
        / "execution_report.json"
    ).write_text(
        json.dumps(
            {
                "project_name": "demo",
                "dry_run": False,
                "records": [],
            }
        ),
        encoding="utf-8",
    )

    def fake_run(
        self,
        *,
        project_name,
        project_root,
        output_root,
        run_production_validation=True,
        source_execution_report=None,
    ):
        target = (
            output_root
            / project_name
        )

        target.mkdir(
            parents=True,
            exist_ok=True,
        )

        (
            target
            / "delivery_report.json"
        ).write_text(
            json.dumps(
                {
                    "project_name": project_name,
                    "overall_status": "ready",
                    "blocker_summary": {},
                    "checks": [],
                }
            ),
            encoding="utf-8",
        )

        return type(
            "FakeDeliveryReport",
            (),
            {"checks": []},
        )()


    monkeypatch.setattr(
        "app.orchestration.orchestrator.DeliveryEngine.run",
        fake_run,
    )

    state = o.run_delivery(
        "demo"
    )

    assert root.is_dir()

    assert (
        o.runtime_root
        / "delivery"
        / "demo"
        / "delivery_report.json"
    ).is_file()

    assert state.current_stage == "economics"
