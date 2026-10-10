import json
from pathlib import Path

from app.discovery.normalizer import RequirementNormalizer
from app.execution.qa import DeterministicQA


CLOUDFORGE_BRIEF = """
Saya ingin dibuatkan website landing page profesional untuk layanan cloud computing bernama CloudForge.

Target pengguna utama adalah UMKM dan startup yang membutuhkan bantuan deployment aplikasi,
monitoring server, dan setup infrastruktur cloud.

Saya ingin tampilannya modern, clean, profesional, menggunakan dark theme,
dan responsive di desktop maupun mobile.

Bagian utama website yang saya butuhkan adalah Hero, Services, About, Benefits, CTA, dan Contact.
Pada bagian Hero harus ada tombol "Get Started" yang mengarah ke bagian Contact.

Layanan yang perlu ditampilkan minimal Cloud Deployment, Server Monitoring,
dan Infrastructure Setup.

Website cukup menggunakan HTML, CSS, dan JavaScript sederhana tanpa framework.
Tidak perlu backend, database, login, payment, maupun deployment ke internet.

Website harus bisa dijalankan secara lokal dan seluruh navigasi serta tombol harus berfungsi.
"""


def test_cloudforge_brief_preserves_sections_and_technology_constraints():
    normalizer = RequirementNormalizer()
    items = {
        item.key: item.value
        for item in normalizer.extract_prompt_confirmed(CLOUDFORGE_BRIEF)
    }

    sections = set(items["required_sections"])

    assert {
        "hero",
        "services",
        "about",
        "benefits",
        "cta",
        "contact",
    }.issubset(sections)

    assert set(items["technology_constraints"]) == {
        "html",
        "css",
        "javascript",
        "no_framework",
    }


def test_cloudforge_brief_preserves_explicit_client_constraints():
    normalizer = RequirementNormalizer()
    items = {
        item.key: item.value
        for item in normalizer.extract_prompt_confirmed(CLOUDFORGE_BRIEF)
    }

    constraints = "\n".join(items["explicit_constraints"])

    assert "Get Started" in constraints
    assert "Cloud Deployment" in constraints
    assert "Server Monitoring" in constraints
    assert "Infrastructure Setup" in constraints
    assert "tanpa framework" in constraints.lower()


def test_node_test_script_is_run_without_jest_specific_arguments(
    tmp_path,
    monkeypatch,
):
    (tmp_path / "package.json").write_text(
        json.dumps({
            "scripts": {
                "test": "node --test",
            }
        }),
        encoding="utf-8",
    )

    qa = DeterministicQA()
    monkeypatch.setattr(qa, "_npm_cmd", lambda: "npm.cmd")

    commands = qa.detect_commands(
        tmp_path,
        "Run deterministic validation/lint/tests",
    )

    assert ["npm.cmd", "test"] in commands

    flattened = [
        part
        for command in commands
        for part in command
    ]

    assert "--runInBand" not in flattened


def test_execution_engine_contains_linear_fail_fast_guard():
    source = (
        Path(__file__).parents[1]
        / "app"
        / "execution"
        / "engine.py"
    ).read_text(encoding="utf-8")

    assert 'if any(record.status == "failed" for record in records):' in source
    assert 'print("? Execution stopped: previous task failed.")' in source


def test_responsive_audit_reads_static_assets_and_root_html(tmp_path):
    (tmp_path / "assets" / "css").mkdir(parents=True)

    (tmp_path / "index.html").write_text(
        """<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body></body>
</html>
""",
        encoding="utf-8",
    )

    (tmp_path / "assets" / "css" / "styles.css").write_text(
        """
.hero {
  font-size: clamp(2rem, 5vw, 4rem);
  max-width: 60rem;
}

@media (width < 40rem) {
  .hero {
    max-width: 100%;
  }
}
""",
        encoding="utf-8",
    )

    qa = DeterministicQA()
    _, result = qa._responsive_audit(tmp_path)

    assert result.returncode == 0
    assert "@media" in result.stdout
    assert "clamp(" in result.stdout
