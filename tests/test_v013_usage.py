import json

from app.execution.usage import (
    UsageLedger,
    parse_claude_usage,
    parse_codex_usage,
)


def test_parse_codex_usage():
    raw = "\n".join([
        json.dumps({"type": "turn.started"}),
        json.dumps({
            "type": "turn.completed",
            "usage": {
                "input_tokens": 15680,
                "cached_input_tokens": 12544,
                "cache_write_input_tokens": 0,
                "output_tokens": 5,
                "reasoning_output_tokens": 2,
            },
        }),
    ])

    usage = parse_codex_usage(raw)

    assert usage is not None
    assert usage.provider == "openai"
    assert usage.input_tokens == 15680
    assert usage.cached_input_tokens == 12544
    assert usage.output_tokens == 5
    assert usage.reasoning_output_tokens == 2
    assert usage.estimated is False


def test_parse_claude_usage():
    raw = json.dumps({
        "type": "result",
        "modelUsage": {
            "claude-opus-5-5": {
                "inputTokens": 2,
                "outputTokens": 4,
                "cacheReadInputTokens": 13948,
                "cacheCreationInputTokens": 11170,
                "thinkingTokens": 0,
                "costUSD": 0.0922376,
                "costBasis": "list",
            }
        },
    })

    usage = parse_claude_usage(raw)

    assert usage is not None
    assert usage.provider == "anthropic"
    assert usage.model == "claude-opus-5-5"
    assert usage.input_tokens == 2
    assert usage.cached_input_tokens == 13948
    assert usage.cache_write_input_tokens == 11170
    assert usage.output_tokens == 4
    assert usage.provider_reported_cost_usd == 0.0922376
    assert usage.cost_basis == "list"
    assert usage.estimated is False


def test_usage_ledger_jsonl(tmp_path):
    usage = parse_claude_usage(json.dumps({
        "modelUsage": {
            "claude-sonnet": {
                "inputTokens": 10,
                "outputTokens": 3,
                "cacheReadInputTokens": 2,
                "cacheCreationInputTokens": 1,
                "costUSD": 0.01,
            }
        }
    }))

    assert usage is not None

    ledger = UsageLedger(tmp_path)

    path = ledger.append(
        project_name="demo",
        task_id="TASK-001",
        owner="claude_code",
        phase="implementation",
        metrics=usage,
    )

    rows = path.read_text(encoding="utf-8").splitlines()

    assert len(rows) == 1

    payload = json.loads(rows[0])

    assert payload["project_name"] == "demo"
    assert payload["task_id"] == "TASK-001"
    assert payload["owner"] == "claude_code"
    assert payload["phase"] == "implementation"
    assert payload["metrics"]["estimated"] is False
