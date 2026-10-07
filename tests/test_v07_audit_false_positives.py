from app.execution.qa import DeterministicQA


def test_requirements_audit_does_not_treat_e2e_validation_as_implementation(tmp_path):
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
        """## Frontend
- [x] Implement about section
- [x] Implement contact section

## Contact Form
- [x] Implement form fields: name, email, company, message
- [ ] Validate submission flow end-to-end

## QA
- [ ] Verify implementation against every confirmed requirement
""",
        encoding="utf-8",
    )
    (tmp_path / "src" / "page.tsx").write_text(
        "about contact name email company message",
        encoding="utf-8",
    )

    _, proc = DeterministicQA()._requirements_audit(tmp_path)
    assert proc.returncode == 0
    assert "unchecked_implementation_tasks=0" in proc.stdout


def test_scope_audit_ignores_portfolio_copy_about_databases(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "src" / "content").mkdir(parents=True)
    (tmp_path / "src" / "app").mkdir(parents=True)

    (tmp_path / "docs" / "backend.md").write_text(
        """## Out of Scope
- No additional API, authentication, database, CRM, or admin functionality unless separately confirmed.
""",
        encoding="utf-8",
    )
    (tmp_path / "package.json").write_text(
        '{"dependencies":{"next":"16.4.0","react":"19.3.0"}}',
        encoding="utf-8",
    )
    (tmp_path / "src" / "content" / "projects.ts").write_text(
        'export const text = "Built pipelines from operational databases";',
        encoding="utf-8",
    )
    (tmp_path / "src" / "app" / "page.tsx").write_text(
        'export default function Page(){ return null }',
        encoding="utf-8",
    )

    _, proc = DeterministicQA()._scope_audit(tmp_path)
    assert proc.returncode == 0


def test_scope_audit_detects_real_database_dependency(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "src").mkdir()

    (tmp_path / "docs" / "backend.md").write_text(
        """## Out of Scope
- No additional API, authentication, database, CRM, or admin functionality unless separately confirmed.
""",
        encoding="utf-8",
    )
    (tmp_path / "package.json").write_text(
        '{"dependencies":{"next":"16.4.0","@prisma/client":"6.0.0"}}',
        encoding="utf-8",
    )

    _, proc = DeterministicQA()._scope_audit(tmp_path)
    assert proc.returncode == 1
    assert "@prisma/client" in proc.stderr
