from app.discovery.engine import RequirementDiscoveryEngine
from app.discovery.normalizer import RequirementNormalizer

def test_reference_urls_are_confirmed_not_fake_style():
    result = RequirementDiscoveryEngine().analyze(
        "Saya ingin portfolio Data Engineering. Targetnya recruiter.",
        ["https://example.com"]
    )
    confirmed = {x.key: x.value for x in result.confirmed}
    assert confirmed["reference_urls"] == ["https://example.com"]
    assert not any(x.key == "reference_style_direction" for x in result.inferred)
    assert any(x.key == "reference_preferences" for x in result.unknown)

def test_reference_preferences_from_prompt_are_confirmed():
    result = RequirementDiscoveryEngine().analyze(
        "Saya suka referensi ini untuk layout dan animasi.",
        ["https://example.com"]
    )
    confirmed = {x.key: x.value for x in result.confirmed}
    assert confirmed["reference_preferences"] == ["animation", "layout"]

def test_contoh_maps_to_default_contact_fields():
    norm = RequirementNormalizer()
    assert norm.normalize_contact_fields("contoh") == ["name", "email", "message"]

def test_semua_is_detected_as_ambiguous():
    norm = RequirementNormalizer()
    assert norm.is_all_sections_answer("semua")
    assert len(norm.standard_portfolio_sections()) >= 5
