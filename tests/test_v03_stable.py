from app.discovery.engine import RequirementDiscoveryEngine
from app.discovery.normalizer import RequirementNormalizer

def test_vague_prompt_extracts_dark_professional_and_goal():
    result = RequirementDiscoveryEngine().analyze(
        "Bikin portfolio data engineer yang keliatan keren dan profesional buat cari kerja. "
        "Gue suka yang dark dan simple. Sisanya bebas kasih saran."
    )
    data = {x.key: x.value for x in result.confirmed}
    assert data["theme"] == "dark"
    assert "professional" in data["visual_direction"]
    assert "minimalist" in data["visual_direction"]
    assert data["project_goal"] == "job_search"
    assert data["portfolio_focus"] == "data engineer" or str(data["portfolio_focus"]).lower() == "data engineer"
    assert result.proposed

def test_detailed_contact_prompt_extracted_without_reasking():
    result = RequirementDiscoveryEngine().analyze(
        "Buat portfolio Data Engineering dengan dark theme, target recruiter dan calon client, "
        "section wajib hero, about, skills, experience, projects, contact. "
        "Contact form kirim ke email dan field wajib nama, email, company, message."
    )
    data = {x.key: x.value for x in result.confirmed}
    assert data["contact_behavior"] == "contact_form"
    assert data["contact_destination"] == "email"
    assert data["contact_fields"] == ["name", "email", "company", "message"]
    unknown = {x.key for x in result.unknown}
    assert "contact_behavior" not in unknown

def test_sesuai_contoh_resolves_to_default_fields():
    norm = RequirementNormalizer()
    assert norm.normalize_contact_fields("sesuai contoh") == ["name", "email", "message"]

def test_manual_sections_normalize_to_canonical_list():
    norm = RequirementNormalizer()
    assert norm.normalize_sections(
        "about, project, sertifikasi, pengalaman, contact"
    ) == ["about", "certifications", "contact", "experience", "projects"]
