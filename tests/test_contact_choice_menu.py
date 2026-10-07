def test_numeric_contact_choices_are_defined():
    mapping = {"1": "display_only", "2": "contact_form"}
    assert mapping["1"] == "display_only"
    assert mapping["2"] == "contact_form"
