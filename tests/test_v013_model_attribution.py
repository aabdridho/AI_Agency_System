import json

from app.execution.adapters import ClaudeCodeAdapter, CodexAdapter
from app.execution.usage import UsageLedger, parse_codex_usage
from app.routing.policy import RoutingPolicy
from app.routing.goat_config import GoatConfig


def test_backend_routing_has_explicit_codex_model(tmp_path):
    policy = RoutingPolicy(
        goat_config=GoatConfig(tmp_path / "missing-tiers.json")
    )

    decision = policy.decide(
        task_id="TASK-001",
        task_text="Create a backend health endpoint.",
        category="backend",
        confidence=0.97,
    )

    assert decision.primary_owner == "codex"
    assert decision.primary_model == "gpt-6.1-sol"
    assert decision.primary_effort == "medium"
    assert decision.fallback_model == "gpt-6-astra"


def test_frontend_build_task_uses_runtime_build_tier(tmp_path):
    policy = RoutingPolicy(
        goat_config=GoatConfig(tmp_path / "missing-tiers.json")
    )

    decision = policy.decide(
        task_id="TASK-002",
        task_text="Create a frontend landing page.",
        category="frontend",
        confidence=0.92,
    )

    assert decision.goat_tier == "build"
    assert decision.primary_owner == "codex"
    assert decision.primary_model == "gpt-6.1-sol"
    assert decision.primary_effort == "medium"
    assert decision.fallback_model == "gpt-6-astra"


def test_codex_command_includes_explicit_model():
    cmd = CodexAdapter().build_command(
        "hello",
        model="gpt-6.1-sol",
        effort="medium",
    )

    assert "--model" in cmd
    assert cmd[cmd.index("--model") + 1] == "gpt-6.1-sol"
    assert "--json" in cmd


def test_claude_command_includes_explicit_model_and_effort():
    cmd = ClaudeCodeAdapter().build_command(
        "hello",
        model="sonnet",
        effort="medium",
    )

    assert "--model" in cmd
    assert cmd[cmd.index("--model") + 1] == "sonnet"
    assert "--effort" in cmd
    assert cmd[cmd.index("--effort") + 1] == "medium"


def test_codex_requested_model_can_fill_missing_cli_model(tmp_path):
    raw = json.dumps({
        "type": "turn.completed",
        "usage": {
            "input_tokens": 100,
            "cached_input_tokens": 80,
            "cache_write_input_tokens": 0,
            "output_tokens": 10,
            "reasoning_output_tokens": 2,
        },
    })

    metrics = parse_codex_usage(raw)

    assert metrics is not None
    assert metrics.model is None

    metrics = metrics.model_copy(update={
        "model": "gpt-6.1-sol",
        "model_source": "execution_request",
        "requested_effort": "medium",
    })

    ledger = UsageLedger(tmp_path)
    path = ledger.append(
        project_name="demo",
        task_id="TASK-001",
        owner="codex",
        phase="implementation",
        metrics=metrics,
    )

    row = json.loads(path.read_text(encoding="utf-8").strip())

    assert row["metrics"]["model"] == "gpt-6.1-sol"
    assert row["metrics"]["model_source"] == "execution_request"
    assert row["metrics"]["requested_effort"] == "medium"
