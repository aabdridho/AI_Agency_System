from app.discovery.engine import RequirementDiscoveryEngine


PROOF_BRIEF = (
    "Buat website landing page sederhana untuk jasa cloud computing freelance. "
    "Halaman memiliki hero section, services section, about section, dan "
    "contact section. Gunakan tema modern minimalis. Contact hanya menampilkan "
    "email, tidak perlu form. Jangan tambahkan authentication, database, "
    "atau fitur lain di luar kebutuhan tersebut."
)


def _confirmed(result):
    return {
        item.key: item.value
        for item in result.confirmed
    }


def test_discovery_understands_explicit_feature_negation():
    result = RequirementDiscoveryEngine().analyze(
        PROOF_BRIEF
    )

    confirmed = _confirmed(result)

    assert confirmed["authentication"] is False
    assert confirmed["database"] is False


def test_discovery_detects_services_section():
    result = RequirementDiscoveryEngine().analyze(
        PROOF_BRIEF
    )

    confirmed = _confirmed(result)

    assert set(
        confirmed["required_sections"]
    ) == {
        "hero",
        "services",
        "about",
        "contact",
    }


def test_discovery_understands_display_only_contact():
    result = RequirementDiscoveryEngine().analyze(
        PROOF_BRIEF
    )

    confirmed = _confirmed(result)

    assert (
        confirmed["contact_behavior"]
        == "display_only"
    )

    assert (
        confirmed["contact_destination"]
        == "email"
    )


def test_positive_feature_mentions_remain_true():
    result = RequirementDiscoveryEngine().analyze(
        "Buat landing page dengan login dan database."
    )

    confirmed = _confirmed(result)

    assert confirmed["authentication"] is True
    assert confirmed["database"] is True


def test_contrast_can_override_prior_negation_clause():
    result = RequirementDiscoveryEngine().analyze(
        "Jangan pakai authentication, tapi database wajib."
    )

    confirmed = _confirmed(result)

    assert confirmed["authentication"] is False
    assert confirmed["database"] is True
