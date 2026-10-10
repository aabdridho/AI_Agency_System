import json
from pathlib import Path

from app.execution.qa import DeterministicQA


def _node_repo(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "scripts": {
                    "lint": "eslint .",
                    "typecheck": "tsc --noEmit",
                    "test": "node --test tests/*.test.mjs",
                    "build": "next build",
                }
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_profiles_are_task_specific():
    qa = DeterministicQA()
    assert qa.profile_for("Validate submission flow end-to-end").name == "submission_e2e"
    assert qa.profile_for("Verify implementation against every confirmed requirement").name == "requirements_audit"
    assert qa.profile_for("Run deterministic validation/lint/tests").name == "validation"
    assert qa.profile_for("Check responsive behavior where applicable").name == "responsive_audit"
    assert qa.profile_for("Confirm no unapproved scope was introduced").name == "scope_audit"


def test_validation_profile_runs_full_node_suite(tmp_path, monkeypatch):
    _node_repo(tmp_path)
    monkeypatch.setattr(
        "shutil.which",
        lambda name: "C:/Program Files/nodejs/npm.cmd" if name == "npm.cmd" else None,
    )
    qa = DeterministicQA()
    commands = qa.detect_commands(tmp_path, "Run deterministic validation/lint/tests")
    assert commands == [
        ["npm.cmd", "run", "lint"],
        ["npm.cmd", "run", "typecheck"],
        ["npm.cmd", "test"],
        ["npm.cmd", "run", "build"],
    ]


def test_requirements_audit_passes_completed_project(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "docs" / "requirement.md").write_text(
        """# Project Requirements
CLIENT_APPROVED
- Ready for development: True
- **required_sections**: about, contact
- **contact_fields**: name, email, company, message
""",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "task.md").write_text(
        """## Setup
- [x] Initialize project
## Frontend
- [x] Implement about
- [x] Implement contact
## QA
- [ ] Verify implementation
""",
        encoding="utf-8",
    )
    (tmp_path / "src" / "page.tsx").write_text(
        "about contact name email company message",
        encoding="utf-8",
    )
    qa = DeterministicQA()
    _, proc = qa._requirements_audit(tmp_path)
    assert proc.returncode == 0


def test_responsive_audit_requires_multiple_markers(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "styles.css").write_text(
        ".x{display:grid;grid-template-columns:repeat(auto-fit,minmax(16rem,1fr));max-width:70rem}",
        encoding="utf-8",
    )
    qa = DeterministicQA()
    _, proc = qa._responsive_audit(tmp_path)
    assert proc.returncode == 0


def test_submission_audit_requires_targeted_test_evidence(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "contact.ts").write_text(
        "POST /api/contact name email company message submit",
        encoding="utf-8",
    )
    (tmp_path / "tests" / "contact.test.mjs").write_text(
        "contact email submission provider",
        encoding="utf-8",
    )
    qa = DeterministicQA()
    _, proc = qa._submission_audit(tmp_path)
    assert proc.returncode == 0
