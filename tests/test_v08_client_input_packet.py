from pathlib import Path

from app.delivery.client_input import ClientInputPacketGenerator
from app.delivery.models import ReadinessCheck


def _placeholder_check(detail):
    return ReadinessCheck(
        check_id="placeholder_content",
        title="Placeholder/client content",
        status="blocker",
        detail=detail,
        blocker_class="CLIENT_INPUT_REQUIRED",
    )


def test_packet_extracts_known_content_sections(tmp_path):
    checks = [
        _placeholder_check(
            "Potential placeholder content found in 3 file(s): "
            "src/content/about.ts, src/content/contact.ts, src/content/hero.ts"
        )
    ]

    generator = ClientInputPacketGenerator(tmp_path)
    items = generator.build_items(checks)

    assert [i.section for i in items] == ["about", "contact", "hero"]
    assert any("biography" in f.lower() for f in items[0].fields)
    assert any("email" in f.lower() for f in items[1].fields)
    assert any("headline" in f.lower() for f in items[2].fields)


def test_packet_never_invents_client_values(tmp_path):
    checks = [
        _placeholder_check(
            "Potential placeholder content found in 1 file(s): src/content/hero.ts"
        )
    ]

    text = ClientInputPacketGenerator(tmp_path).render_markdown(
        project_name="demo",
        checks=checks,
    )

    assert "Full name / display name" in text
    assert "Do not invent or infer personal/client facts." in text
    assert "approved for public display" in text


def test_no_packet_when_no_client_input_blocker(tmp_path):
    checks = [
        ReadinessCheck(
            check_id="git_clean",
            title="Git working tree",
            status="pass",
            detail="clean",
        )
    ]

    assert (
        ClientInputPacketGenerator(tmp_path).render_markdown(
            project_name="demo",
            checks=checks,
        )
        is None
    )


def test_requirement_gate_creates_approval_request(tmp_path):
    checks = [
        ReadinessCheck(
            check_id="requirement_gate",
            title="Requirement approval gate",
            status="blocker",
            detail="not approved",
            blocker_class="CLIENT_INPUT_REQUIRED",
        )
    ]

    items = ClientInputPacketGenerator(tmp_path).build_items(checks)
    assert len(items) == 1
    assert items[0].section == "requirements_approval"
