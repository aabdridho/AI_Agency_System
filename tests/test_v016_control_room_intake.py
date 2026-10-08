from fastapi.testclient import TestClient

import api
from app.models.schemas import DiscoveryResult, RequirementItem


class FakeOrchestrator:
    def __init__(self):
        self.calls = []

    def analyze_brief(self, brief, references=None):
        self.calls.append((brief, references))

        return DiscoveryResult(
            project_type="website",
            confirmed=[
                RequirementItem(
                    key="goal",
                    value="company profile",
                    status="CONFIRMED",
                    source="client_prompt",
                    blocking=False,
                    confidence=1.0,
                )
            ],
            inferred=[],
            proposed=[],
            unknown=[
                RequirementItem(
                    key="contact_email",
                    value=None,
                    status="UNKNOWN",
                    source="gap_detector",
                    blocking=True,
                )
            ],
            internal_decisions=[],
            questions=["Email kontak yang ingin ditampilkan apa?"],
            ready_for_final_approval=False,
            client_approved=False,
            ready_for_development=False,
        )


def test_project_intake_analyzes_brief_without_execution():
    fake = FakeOrchestrator()
    api.app.dependency_overrides[api.get_orchestrator] = lambda: fake

    try:
        client = TestClient(api.app)

        response = client.post(
            "/api/projects/intake",
            json={
                "project_name": "website-pt-abc",
                "brief": "Buat website company profile.",
                "references": ["https://example.com"],
            },
        )

        assert response.status_code == 200

        payload = response.json()

        assert payload["project_name"] == "website-pt-abc"
        assert payload["discovery"]["project_type"] == "website"
        assert payload["discovery"]["questions"] == [
            "Email kontak yang ingin ditampilkan apa?"
        ]

        assert fake.calls == [
            (
                "Buat website company profile.",
                ["https://example.com"],
            )
        ]
    finally:
        api.app.dependency_overrides.clear()


def test_project_intake_rejects_invalid_project_name():
    fake = FakeOrchestrator()
    api.app.dependency_overrides[api.get_orchestrator] = lambda: fake

    try:
        client = TestClient(api.app)

        response = client.post(
            "/api/projects/intake",
            json={
                "project_name": "../secret",
                "brief": "Buat website.",
                "references": [],
            },
        )

        assert response.status_code == 422
        assert fake.calls == []
    finally:
        api.app.dependency_overrides.clear()


def test_project_intake_rejects_empty_brief():
    client = TestClient(api.app)

    response = client.post(
        "/api/projects/intake",
        json={
            "project_name": "demo",
            "brief": "",
            "references": [],
        },
    )

    assert response.status_code == 422
