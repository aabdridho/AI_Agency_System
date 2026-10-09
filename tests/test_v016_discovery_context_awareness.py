from app.discovery.engine import RequirementDiscoveryEngine


BRIEF = """
Buat landing page untuk jasa konsultasi cloud.
Target utama UMKM dan startup.
Tampilan minimalis, profesional, dan modern.
Halaman memiliki hero, layanan, tentang kami, dan kontak.
Tidak memerlukan login, database, maupun pembayaran.
"""


def confirmed_by_key(result):
    return {
        item.key: item
        for item in result.confirmed
    }


def test_explicit_audience_is_not_asked_again():
    result = RequirementDiscoveryEngine().analyze(BRIEF)

    confirmed = confirmed_by_key(result)

    assert "target_audience" in confirmed

    audience = str(
        confirmed["target_audience"].value
    ).lower()

    assert "umkm" in audience
    assert "startup" in audience

    assert not any(
        item.key == "target_audience"
        for item in result.unknown
    )


def test_visual_direction_is_extracted():
    result = RequirementDiscoveryEngine().analyze(BRIEF)

    visual = set(
        confirmed_by_key(result)[
            "visual_direction"
        ].value
    )

    assert {
        "minimalist",
        "modern",
        "professional",
    }.issubset(visual)


def test_required_sections_are_extracted():
    result = RequirementDiscoveryEngine().analyze(BRIEF)

    sections = set(
        confirmed_by_key(result)[
            "required_sections"
        ].value
    )

    assert {
        "hero",
        "services",
        "about",
        "contact",
    }.issubset(sections)


def test_explicit_exclusions_are_preserved():
    result = RequirementDiscoveryEngine().analyze(BRIEF)

    confirmed = confirmed_by_key(result)

    assert confirmed["authentication"].value is False
    assert confirmed["database"].value is False
    assert confirmed["payment"].value is False


def test_already_answered_requirements_are_not_reasked():
    result = RequirementDiscoveryEngine().analyze(BRIEF)

    question_text = " ".join(
        result.questions
    ).lower()

    assert "siapa target utama" not in question_text
    assert "gaya visual seperti apa" not in question_text
    assert "fitur apa saja yang wajib" not in question_text


def test_remaining_question_is_contextual():
    result = RequirementDiscoveryEngine().analyze(BRIEF)

    assert result.questions == [
        (
            "Setelah target audience UMKM dan startup "
            "melihat landing page ini, aksi utama apa "
            "yang ingin diarahkan: WhatsApp, "
            "form konsultasi, email, atau booking meeting?"
        )
    ]
