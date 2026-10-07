from app.discovery.engine import RequirementDiscoveryEngine
from app.discovery.confirmation import ConfirmationGate
from app.discovery.normalizer import RequirementNormalizer

PROMPT = (
    "Saya ingin dibuatkan website portfolio untuk Data Engineering. "
    "Saya suka website yang tampilannya clean, modern, dan tidak terlalu ramai. "
    "Saya ingin ada bagian tentang saya, skill, pengalaman, project, dan kontak. "
    "Untuk warna saya lebih suka dark theme. "
    "Target website ini untuk recruiter dan perusahaan teknologi."
)

def test_smart_extraction():
    result = RequirementDiscoveryEngine().analyze(PROMPT)

    assert any(x.key == "portfolio_focus" and x.value == "Data Engineering" for x in result.confirmed)
    assert any(x.key == "theme" and x.value == "dark" for x in result.confirmed)
    assert any(x.key == "visual_direction" for x in result.confirmed)
    assert any(x.key == "required_sections" for x in result.confirmed)
    assert any(x.key == "target_audience" for x in result.confirmed)

def test_no_duplicate_questions_for_extracted_fields():
    result = RequirementDiscoveryEngine().analyze(PROMPT)
    unknown_keys = {x.key for x in result.unknown}
    assert "target_audience" not in unknown_keys
    assert "visual_direction" not in unknown_keys
    assert "required_sections" not in unknown_keys
    assert "contact_behavior" in unknown_keys

def test_contact_answer_normalization():
    norm = RequirementNormalizer()
    assert norm.normalize_contact_behavior("mengisi data bisa supaya memudahkan client") == "contact_form"

def test_proposals_need_confirmation():
    prompt = (
        "Buat portfolio Data Engineering. "
        "Section wajib about, project, contact. "
        "Sisanya bisa dikembangkan sesuai pasaran."
    )
    result = RequirementDiscoveryEngine().analyze(prompt)
    assert result.proposed

def test_final_approval_gate():
    result = RequirementDiscoveryEngine().analyze(PROMPT)
    assert result.ready_for_development is False
    assert result.client_approved is False
