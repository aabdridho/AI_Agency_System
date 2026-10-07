from pathlib import Path

import pytest

from app.documentation.generator import ProjectDocumentationGenerator
from app.models.schemas import DiscoveryResult, RequirementItem


def item(key, value, status="CONFIRMED", source="test"):
    return RequirementItem(
        key=key,
        value=value,
        status=status,
        source=source,
        blocking=False,
        confidence=1.0,
    )


def approved_result(contact_behavior="contact_form"):
    confirmed = [
        item("portfolio_focus", "Data Engineering"),
        item("visual_direction", ["minimalist", "modern"]),
        item("theme", "dark"),
        item("required_sections", ["hero", "about", "projects", "contact"]),
        item("target_audience", "recruiter / HR"),
        item("contact_behavior", contact_behavior),
    ]
    if contact_behavior == "contact_form":
        confirmed += [
            item("contact_destination", "email"),
            item("contact_fields", ["name", "email", "message"]),
        ]

    return DiscoveryResult(
        project_type="portfolio",
        confirmed=confirmed,
        inferred=[],
        proposed=[],
        unknown=[],
        internal_decisions=[
            item(
                "deployment_target",
                "to_be_decided_internally",
                status="INTERNAL_DECISION",
                source="system",
            )
        ],
        questions=[],
        ready_for_final_approval=True,
        client_approved=True,
        ready_for_development=True,
    )


def test_generates_core_docs(tmp_path):
    result = approved_result()
    files = ProjectDocumentationGenerator().generate(result, tmp_path / "project")
    names = {p.name for p in files}

    assert "requirement.md" in names
    assert "task.md" in names
    assert "architecture.md" in names
    assert "deployment.md" in names
    assert "discovery.md" in names
    assert "CHANGELOG.md" in names


def test_frontend_generated_for_portfolio(tmp_path):
    result = approved_result()
    ProjectDocumentationGenerator().generate(result, tmp_path / "project")
    assert (tmp_path / "project/docs/frontend.md").exists()


def test_backend_generated_for_contact_form(tmp_path):
    result = approved_result("contact_form")
    ProjectDocumentationGenerator().generate(result, tmp_path / "project")
    assert (tmp_path / "project/docs/backend.md").exists()


def test_backend_not_generated_for_display_only(tmp_path):
    result = approved_result("display_only")
    ProjectDocumentationGenerator().generate(result, tmp_path / "project")
    assert not (tmp_path / "project/docs/backend.md").exists()


def test_task_is_derived_from_required_sections(tmp_path):
    result = approved_result()
    ProjectDocumentationGenerator().generate(result, tmp_path / "project")
    task = (tmp_path / "project/docs/task.md").read_text(encoding="utf-8")
    assert "Implement `hero` section" in task
    assert "Implement `projects` section" in task
    assert "Submit form data to `email`" in task


def test_backend_does_not_invent_extra_scope(tmp_path):
    result = approved_result()
    ProjectDocumentationGenerator().generate(result, tmp_path / "project")
    backend = (tmp_path / "project/docs/backend.md").read_text(encoding="utf-8")
    assert "No additional API, authentication, database, CRM, or admin functionality" in backend


def test_unapproved_project_cannot_generate_final_docs(tmp_path):
    result = approved_result()
    result = result.model_copy(update={
        "client_approved": False,
        "ready_for_development": False,
    })
    with pytest.raises(ValueError):
        ProjectDocumentationGenerator().generate(result, tmp_path / "project")
