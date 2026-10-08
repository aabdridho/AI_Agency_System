from types import SimpleNamespace

import app.orchestration.orchestrator as orchestration_module


class _Check:
    def __init__(
        self,
        *,
        blocker_class=None,
        auto_resolvable=False,
        status="blocker",
    ):
        self.status = status
        self.blocker_class = blocker_class
        self.auto_resolvable = auto_resolvable


def _report(*checks):
    return SimpleNamespace(
        checks=list(checks),
    )


def test_delivery_auto_resolves_internal_blocker(
    tmp_path,
    monkeypatch,
):
    runtime = tmp_path / "runtime"
    output = tmp_path / "output"
    project = output / "demo"

    project.mkdir(parents=True)

    calls = {
        "delivery": 0,
        "resolver": 0,
    }

    reports = [
        _report(
            _Check(
                blocker_class="AUTO_RESOLVABLE_INTERNAL",
                auto_resolvable=True,
            )
        ),
        _report(),
    ]

    class FakeDeliveryEngine:
        def run(self, **kwargs):
            index = calls["delivery"]
            calls["delivery"] += 1
            return reports[index]

    class FakeResolver:
        def __init__(self, repo):
            self.repo = repo

        def resolve_deployment_target_to_vercel(self):
            calls["resolver"] += 1
            return {
                "resolution": "deployment_target=vercel",
            }

    monkeypatch.setattr(
        orchestration_module,
        "DeliveryEngine",
        FakeDeliveryEngine,
    )

    monkeypatch.setattr(
        orchestration_module,
        "InternalResolver",
        FakeResolver,
    )

    orchestrator = (
        orchestration_module.ProjectOrchestrator(
            runtime_root=runtime,
            output_root=output,
        )
    )

    monkeypatch.setattr(
        orchestrator,
        "resume",
        lambda project_name: SimpleNamespace(
            project_name=project_name
        ),
    )

    orchestrator.run_delivery("demo")

    assert calls["resolver"] == 1
    assert calls["delivery"] == 2


def test_delivery_does_not_auto_resolve_with_hard_blocker(
    tmp_path,
    monkeypatch,
):
    runtime = tmp_path / "runtime"
    output = tmp_path / "output"
    project = output / "demo"

    project.mkdir(parents=True)

    calls = {
        "resolver": 0,
    }

    class FakeDeliveryEngine:
        def run(self, **kwargs):
            return _report(
                _Check(
                    blocker_class="AUTO_RESOLVABLE_INTERNAL",
                    auto_resolvable=True,
                ),
                _Check(
                    blocker_class="HARD_TECHNICAL_BLOCKER",
                ),
            )

    class FakeResolver:
        def __init__(self, repo):
            pass

        def resolve_deployment_target_to_vercel(self):
            calls["resolver"] += 1

    monkeypatch.setattr(
        orchestration_module,
        "DeliveryEngine",
        FakeDeliveryEngine,
    )

    monkeypatch.setattr(
        orchestration_module,
        "InternalResolver",
        FakeResolver,
    )

    orchestrator = (
        orchestration_module.ProjectOrchestrator(
            runtime_root=runtime,
            output_root=output,
        )
    )

    monkeypatch.setattr(
        orchestrator,
        "resume",
        lambda project_name: SimpleNamespace(
            project_name=project_name
        ),
    )

    orchestrator.run_delivery("demo")

    assert calls["resolver"] == 0
