from app.discovery.normalizer import RequirementNormalizer
from app.discovery.dependency_expander import DependencyExpander
from app.models.schemas import RequirementItem

def test_mengirimkan_data_normalizes_to_contact_form():
    norm = RequirementNormalizer()
    assert norm.normalize_contact_behavior("mengirimkan data") == "contact_form"

def test_mengirim_data_normalizes_to_contact_form():
    norm = RequirementNormalizer()
    assert norm.normalize_contact_behavior("mengirim data") == "contact_form"

def test_mengisi_data_normalizes_to_contact_form():
    norm = RequirementNormalizer()
    assert norm.normalize_contact_behavior("mengisi data bisa supaya memudahkan client") == "contact_form"

def test_display_only_remains_display_only():
    norm = RequirementNormalizer()
    assert norm.normalize_contact_behavior("hanya menampilkan kontak") == "display_only"

def test_dependency_expands_after_normalized_contact_form():
    confirmed = [
        RequirementItem(
            key="contact_behavior",
            value="contact_form",
            status="CONFIRMED",
            source="test"
        )
    ]
    deps = DependencyExpander().expand(confirmed)
    keys = {x.key for x in deps}
    assert "contact_destination" in keys
    assert "contact_fields" in keys
