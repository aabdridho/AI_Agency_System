from app.discovery.normalizer import RequirementNormalizer

def test_extract_prompt_confirmed_exists_and_extracts():
    norm = RequirementNormalizer()
    items = norm.extract_prompt_confirmed(
        "Website portfolio yang clean, modern, dark theme untuk recruiter. "
        "Ada about, skills, projects, dan contact."
    )
    keys = {x.key for x in items}
    assert "visual_direction" in keys
    assert "theme" in keys
    assert "required_sections" in keys
    assert "target_audience" in keys
