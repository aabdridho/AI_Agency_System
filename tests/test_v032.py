from app.discovery.dependency_expander import DependencyExpander
from app.discovery.deduplicator import SemanticDeduplicator
from app.discovery.normalizer import RequirementNormalizer
from app.models.schemas import RequirementItem

def test_contact_form_expands_dependencies():
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

def test_contact_field_normalization():
    result = RequirementNormalizer().normalize_contact_fields(
        "nama, email, pesan"
    )
    assert result == ["name", "email", "message"]

def test_semantic_deduplication():
    confirmed = [
        RequirementItem(key="contact", value=True, status="CONFIRMED", source="test"),
        RequirementItem(key="portfolio_projects", value=True, status="CONFIRMED", source="test"),
        RequirementItem(
            key="required_sections",
            value=["about", "projects", "contact"],
            status="CONFIRMED",
            source="test"
        ),
    ]

    cleaned = SemanticDeduplicator().clean_confirmed(confirmed)
    keys = {x.key for x in cleaned}

    assert "contact" not in keys
    assert "portfolio_projects" not in keys
    assert "required_sections" in keys
