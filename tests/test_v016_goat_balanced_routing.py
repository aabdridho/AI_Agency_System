from app.routing.goat_config import GoatConfig
from app.routing.policy import RoutingPolicy


def policy(tmp_path):
    return RoutingPolicy(
        goat_config=GoatConfig(
            path=tmp_path / "missing-tiers.json",
        )
    )


def decide(
    tmp_path,
    *,
    text,
    category,
):
    return policy(tmp_path).decide(
        task_id="TASK-001",
        task_text=text,
        category=category,
        confidence=0.95,
    )


def test_frontend_build_prefers_claude(tmp_path):
    result = decide(
        tmp_path,
        text="Implement hero section and responsive UI",
        category="frontend",
    )

    assert result.route == "build"
    assert result.risk == "medium"

    assert result.primary_owner == "claude_code"
    assert result.primary_model == "sonnet"
    assert result.primary_effort == "medium"

    assert result.fallback_owner == "codex"
    assert result.fallback_model == "gpt-6-astra"


def test_backend_build_prefers_codex(tmp_path):
    result = decide(
        tmp_path,
        text="Implement API endpoint for contact submission",
        category="backend",
    )

    assert result.route == "build"

    assert result.primary_owner == "codex"
    assert result.primary_model == "gpt-6.1-sol"
    assert result.primary_effort == "medium"

    assert result.fallback_owner == "claude_code"
    assert result.fallback_model == "fable"


def test_backend_deep_stays_codex_but_higher_effort(tmp_path):
    result = decide(
        tmp_path,
        text="Implement authentication and authorization security",
        category="backend",
    )

    assert result.route == "deep"
    assert result.risk == "high"

    assert result.primary_owner == "codex"
    assert result.primary_model == "gpt-6.1-sol"
    assert result.primary_effort == "high"

    assert result.fallback_owner == "claude_code"


def test_architecture_deep_prefers_claude(tmp_path):
    result = decide(
        tmp_path,
        text="Design repository architecture",
        category="architecture",
    )

    assert result.route == "deep"
    assert result.risk == "high"

    assert result.primary_owner == "claude_code"
    assert result.primary_model == "opus"
    assert result.primary_effort == "high"

    assert result.fallback_owner == "codex"


def test_qa_remains_zero_token_deterministic(tmp_path):
    result = decide(
        tmp_path,
        text="Run deterministic validation",
        category="qa",
    )

    assert result.route == "review"
    assert result.primary_owner == "deterministic_qa"
    assert result.primary_model is None
    assert result.verifier == "deterministic_qa"

    assert result.fallback_owner in {
        "codex",
        "claude_code",
    }


def test_every_route_exposes_checks_and_triage_mode(tmp_path):
    result = decide(
        tmp_path,
        text="Implement contact API",
        category="backend",
    )

    assert result.triage_mode == "rules"
    assert result.checks
    assert "tests" in result.checks
