from fastapi.testclient import TestClient

import api
from app.orchestration.models import OrchestrationState


class FakeExecutionOrchestrator:
    def __init__(self):
        self.calls = []

    def run_until_blocked(
        self,
        project_name,
        *,
        approve_real_execution=False,
    ):
        self.calls.append(
            (project_name, approve_real_execution)
        )

        return OrchestrationState(
            project_name=project_name,
            status="waiting_approval",
            current_stage="deployment",
            completed_stages=[
                "discovery",
                "documentation",
                "routing",
                "execution",
                "delivery",
                "economics",
            ],
            waiting_for="deployment_approval",
        )


def test_execute_endpoint_approves_real_execution():
    fake = FakeExecutionOrchestrator()

    api.app.dependency_overrides[
        api.get_orchestrator
    ] = lambda: fake

    try:
        client = TestClient(api.app)

        response = client.post(
            "/api/projects/demo-site/execute"
        )

        assert response.status_code == 200

        data = response.json()

        assert fake.calls == [
            ("demo-site", True)
        ]

        assert data["status"] == "waiting_approval"
        assert data["current_stage"] == "deployment"
        assert (
            data["waiting_for"]
            == "deployment_approval"
        )
    finally:
        api.app.dependency_overrides.clear()


def test_execute_endpoint_maps_runtime_error_to_409():
    class FailingOrchestrator:
        def run_until_blocked(
            self,
            project_name,
            *,
            approve_real_execution=False,
        ):
            raise RuntimeError(
                "execution preflight gagal"
            )

    api.app.dependency_overrides[
        api.get_orchestrator
    ] = lambda: FailingOrchestrator()

    try:
        client = TestClient(api.app)

        response = client.post(
            "/api/projects/demo-site/execute"
        )

        assert response.status_code == 409
        assert (
            "execution preflight gagal"
            in response.text
        )
    finally:
        api.app.dependency_overrides.clear()
