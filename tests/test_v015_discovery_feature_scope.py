from app.discovery.engine import RequirementDiscoveryEngine
from app.discovery.gap_detector import GapDetector


def test_required_sections_suppress_generic_required_features_gap():
    unknown, questions, question_map = GapDetector().detect(
        "landing_page",
        {"project_goal", "required_sections"},
    )

    assert "required_features" not in {item.key for item in unknown}
    assert "required_features" not in question_map
    assert "Fitur apa saja yang wajib tersedia?" not in questions


def test_vague_landing_page_still_requires_feature_scope():
    unknown, questions, question_map = GapDetector().detect(
        "landing_page",
        {"project_goal"},
    )

    assert "required_features" in {item.key for item in unknown}
    assert "required_features" in question_map
    assert "Fitur apa saja yang wajib tersedia?" in questions


def test_explicit_landing_page_sections_do_not_create_required_features_blocker():
    result = RequirementDiscoveryEngine().analyze(
        "Bikin landing page konsultasi cloud. "
        "Section wajib hero, services, contact. "
        "Contact hanya menampilkan email, tidak perlu form.",
    )

    confirmed = {item.key: item.value for item in result.confirmed}
    unknown_keys = {item.key for item in result.unknown}

    assert confirmed["required_sections"] == ["contact", "hero", "services"]
    assert confirmed["contact_behavior"] == "display_only"
    assert confirmed["contact_destination"] == "email"
    assert "required_features" not in unknown_keys
    assert "Fitur apa saja yang wajib tersedia?" not in result.questions
