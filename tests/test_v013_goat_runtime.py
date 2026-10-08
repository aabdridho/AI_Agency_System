import json

from app.routing.goat_config import GoatConfig, GoatTierClassifier
from app.routing.policy import RoutingPolicy


def save_config(path, tiers):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"tiers": tiers}),
        encoding="utf-8",
    )


def test_goat_defaults_resolve_build_to_sol(tmp_path):
    cfg = GoatConfig(tmp_path / "tiers.json")

    resolved = cfg.resolve("build")

    assert resolved.owner == "codex"
    assert resolved.executable_model == "gpt-6.1-sol"
    assert resolved.effort == "medium"
    assert resolved.source == "goat_default_config"


def test_saved_dashboard_config_changes_real_routing_model(tmp_path):
    path = tmp_path / "tiers.json"

    save_config(
        path,
        {
            "build": {
                "model": "luna",
                "effort": "low",
            }
        },
    )

    policy = RoutingPolicy(
        goat_config=GoatConfig(path)
    )

    d = policy.decide(
        task_id="TASK-001",
        task_text="Create normal backend endpoint",
        category="backend",
        confidence=0.97,
    )

    assert d.goat_tier == "build"
    assert d.primary_owner == "codex"
    assert d.primary_model == "gpt-6-luna"
    assert d.primary_effort == "low"
    assert d.model_source == "goat_runtime_config"


def test_dashboard_can_switch_build_vendor_to_claude(tmp_path):
    path = tmp_path / "tiers.json"

    save_config(
        path,
        {
            "build": {
                "model": "sonnet",
                "effort": "medium",
            }
        },
    )

    policy = RoutingPolicy(
        goat_config=GoatConfig(path)
    )

    d = policy.decide(
        task_id="TASK-001",
        task_text="Implement ordinary feature",
        category="backend",
        confidence=0.90,
    )

    assert d.goat_tier == "build"
    assert d.primary_owner == "claude_code"
    assert d.primary_model == "sonnet"
    assert d.primary_effort == "medium"


def test_quick_task_uses_quick_tier():
    classifier = GoatTierClassifier()

    tier = classifier.classify(
        "Ganti teks hero di landing page",
        "frontend",
    )

    assert tier == "quick"


def test_deep_security_task_uses_deep_tier():
    classifier = GoatTierClassifier()

    tier = classifier.classify(
        "Implement secure authentication and permission system",
        "backend",
    )

    assert tier == "deep"


def test_creative_task_uses_create_tier():
    classifier = GoatTierClassifier()

    tier = classifier.classify(
        "Buat caption promo dan naskah video",
        "general",
    )

    assert tier == "create"


def test_fallback_always_resolves_from_escalation_tier(tmp_path):
    path = tmp_path / "tiers.json"

    save_config(
        path,
        {
            "build": {
                "model": "luna",
                "effort": "low",
            },
            "esc": {
                "model": "astra",
                "effort": "high",
            },
        },
    )

    policy = RoutingPolicy(
        goat_config=GoatConfig(path)
    )

    d = policy.decide(
        task_id="TASK-001",
        task_text="Implement ordinary backend feature",
        category="backend",
        confidence=0.95,
    )

    assert d.primary_model == "gpt-6-luna"
    assert d.fallback_model == "gpt-6-astra"
    assert d.fallback_effort == "high"
    assert d.max_escalations == 1


def test_qa_stays_deterministic_first(tmp_path):
    policy = RoutingPolicy(
        goat_config=GoatConfig(tmp_path / "tiers.json")
    )

    d = policy.decide(
        task_id="TASK-001",
        task_text="Run tests and validate implementation",
        category="qa",
        confidence=0.99,
    )

    assert d.primary_owner == "deterministic_qa"
    assert d.primary_model is None
    assert d.goat_tier == "review"
    assert d.max_escalations == 1


def test_invalid_saved_model_cannot_reach_executor(tmp_path):
    path = tmp_path / "tiers.json"

    save_config(
        path,
        {
            "build": {
                "model": "totally-fake-model",
                "effort": "medium",
            }
        },
    )

    resolved = GoatConfig(path).resolve("build")

    # Invalid browser/runtime input falls back to canonical default.
    assert resolved.executable_model == "gpt-6.1-sol"
    assert resolved.source == "goat_default_config"
