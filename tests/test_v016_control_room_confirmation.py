from pathlib import Path

from fastapi.testclient import TestClient

import api
from app.models.schemas import DiscoveryResult, RequirementItem


def discovery_with_blocker():
    return DiscoveryResult(
        project_type="landing_page",
        confirmed=[],
        inferred=[],
        proposed=[],
        unknown=[
            RequirementItem(
                key="target_audience",
                value=None,
                status="UNKNOWN",
                source="gap_detector",
                blocking=True,
            )
        ],
        internal_decisions=[],
        questions=["Siapa target utama website ini?"],
        ready_for_final_approval=False,
        client_approved=False,
        ready_for_development=False,
    )


def test_confirm_intake_promotes_blocker():
    client = TestClient(api.app)

    response = client.post(
        "/api/projects/intake/confirm",
        json={
            "project_name": "demo-site",
            "result": discovery_with_blocker().model_dump(),
            "answers": {
                "target_audience": "UMKM",
            },
        },
    )

    assert response.status_code == 200

    result = response.json()["discovery"]

    assert result["unknown"] == []
    assert result["confirmed"][0]["key"] == "target_audience"
    assert result["confirmed"][0]["value"] == "UMKM"
    assert result["ready_for_final_approval"] is True
    assert result["ready_for_development"] is False


class FakeApprovalOrchestrator:
    def __init__(self):
        self.approved = False
        self.generated = False

    def approve_discovery(self, result):
        self.approved = True

        return result.model_copy(
            update={
                "client_approved": True,
                "ready_for_final_approval": True,
                "ready_for_development": True,
            }
        )

    def generate_documentation(self, project_name, result):
        assert project_name == "demo-site"
        assert result.ready_for_development is True

        self.generated = True

        return [
            Path("requirement.md"),
            Path("task.md"),
            Path("architecture.md"),
        ]

    def run_until_blocked(
        self,
        project_name,
        *,
        approve_real_execution=False,
    ):
        assert project_name == "demo-site"
        assert approve_real_execution is False
        return None


def test_approve_intake_generates_documentation():
    fake = FakeApprovalOrchestrator()

    api.app.dependency_overrides[
        api.get_orchestrator
    ] = lambda: fake

    try:
        result = discovery_with_blocker()

        result = api.gate.promote_confirmed(
            result,
            "target_audience",
            "UMKM",
        )

        client = TestClient(api.app)

        response = client.post(
            "/api/projects/intake/approve",
            json={
                "project_name": "demo-site",
                "result": result.model_dump(),
            },
        )

        assert response.status_code == 200

        payload = response.json()

        assert payload["discovery"]["client_approved"] is True
        assert (
            payload["discovery"]["ready_for_development"]
            is True
        )

        assert payload["generated_docs"] == [
            "requirement.md",
            "task.md",
            "architecture.md",
        ]

        assert fake.approved is True
        assert fake.generated is True
    finally:
        api.app.dependency_overrides.clear()


def test_approve_intake_rejects_unresolved_blocker():
    class RejectingOrchestrator:
        def approve_discovery(self, result):
            raise ValueError(
                "Discovery belum memenuhi final approval gate."
            )

    fake = RejectingOrchestrator()

    api.app.dependency_overrides[
        api.get_orchestrator
    ] = lambda: fake

    try:
        client = TestClient(api.app)

        response = client.post(
            "/api/projects/intake/approve",
            json={
                "project_name": "demo-site",
                "result": discovery_with_blocker().model_dump(),
            },
        )

        assert response.status_code == 409
    finally:
        api.app.dependency_overrides.clear()
