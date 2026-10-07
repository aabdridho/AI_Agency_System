from app.discovery.normalizer import RequirementNormalizer

def test_bare_kontak_is_ambiguous():
    norm = RequirementNormalizer()
    assert norm.normalize_contact_behavior("kontak") is None

def test_bare_contact_is_ambiguous():
    norm = RequirementNormalizer()
    assert norm.normalize_contact_behavior("contact") is None

def test_kontak_saja_is_display_only():
    norm = RequirementNormalizer()
    assert norm.normalize_contact_behavior("kontak saja") == "display_only"

def test_form_is_contact_form():
    norm = RequirementNormalizer()
    assert norm.normalize_contact_behavior("form") == "contact_form"
