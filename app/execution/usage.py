from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel


class UsageMetrics(BaseModel):
    provider: str
    model: str | None = None

    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_output_tokens: int = 0

    provider_reported_cost_usd: float | None = None
    cost_basis: str | None = None

    usage_source: str = "cli_reported"
    estimated: bool = False

    # Where model attribution came from. Claude normally reports the
    # canonical model itself; Codex 0.160.1 usage events currently do not.
    model_source: str | None = None
    requested_effort: str | None = None
    goat_tier: str | None = None


class UsageRecord(BaseModel):
    timestamp: datetime
    project_name: str
    task_id: str
    owner: str
    phase: str

    # Unique identity for one recorded provider usage row.
    # Optional keeps legacy usage.jsonl readable.
    usage_id: str | None = None

    run_id: str | None = None
    attempt: int = 1

    metrics: UsageMetrics


def parse_codex_usage(stdout: str) -> UsageMetrics | None:
    completed = None

    for raw in (stdout or "").splitlines():
        raw = raw.strip()
        if not raw:
            continue

        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue

        if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
            completed = event

    if not completed:
        return None

    usage = completed["usage"]

    return UsageMetrics(
        provider="openai",
        model=completed.get("model"),
        input_tokens=int(usage.get("input_tokens") or 0),
        cached_input_tokens=int(usage.get("cached_input_tokens") or 0),
        cache_write_input_tokens=int(usage.get("cache_write_input_tokens") or 0),
        output_tokens=int(usage.get("output_tokens") or 0),
        reasoning_output_tokens=int(usage.get("reasoning_output_tokens") or 0),
    )


def parse_claude_usage(stdout: str) -> UsageMetrics | None:
    text = (stdout or "").strip()
    if not text:
        return None

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None

    model_usage = payload.get("modelUsage") or {}
    if not isinstance(model_usage, dict) or not model_usage:
        return None

    model_names: list[str] = []
    input_tokens = 0
    cached_tokens = 0
    cache_write_tokens = 0
    output_tokens = 0
    reasoning_tokens = 0
    reported_cost = 0.0
    saw_cost = False
    cost_bases: set[str] = set()

    for model_name, details in model_usage.items():
        if not isinstance(details, dict):
            continue

        model_names.append(str(model_name))
        input_tokens += int(details.get("inputTokens") or 0)
        cached_tokens += int(details.get("cacheReadInputTokens") or 0)
        cache_write_tokens += int(details.get("cacheCreationInputTokens") or 0)
        output_tokens += int(details.get("outputTokens") or 0)
        reasoning_tokens += int(details.get("thinkingTokens") or 0)

        cost = details.get("costUSD")
        if cost is not None:
            reported_cost += float(cost)
            saw_cost = True

        basis = details.get("costBasis")
        if basis:
            cost_bases.add(str(basis))

    if not model_names:
        return None

    return UsageMetrics(
        provider="anthropic",
        model=",".join(sorted(model_names)),
        model_source="cli_reported",
        input_tokens=input_tokens,
        cached_input_tokens=cached_tokens,
        cache_write_input_tokens=cache_write_tokens,
        output_tokens=output_tokens,
        reasoning_output_tokens=reasoning_tokens,
        provider_reported_cost_usd=reported_cost if saw_cost else None,
        cost_basis=",".join(sorted(cost_bases)) if cost_bases else None,
    )


def parse_usage(owner: str, stdout: str) -> UsageMetrics | None:
    if owner == "codex":
        return parse_codex_usage(stdout)

    if owner == "claude_code":
        return parse_claude_usage(stdout)

    return None


class UsageLedger:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def append(
        self,
        *,
        project_name: str,
        task_id: str,
        owner: str,
        phase: str,
        metrics: UsageMetrics,
        run_id: str | None = None,
        attempt: int = 1,
    ) -> Path:
        directory = self.root / project_name
        directory.mkdir(parents=True, exist_ok=True)

        path = directory / "usage.jsonl"

        record = UsageRecord(
            timestamp=datetime.now(timezone.utc),
            project_name=project_name,
            task_id=task_id,
            owner=owner,
            phase=phase,
            usage_id=uuid4().hex,
            run_id=run_id,
            attempt=attempt,
            metrics=metrics,
        )

        with path.open("a", encoding="utf-8") as fh:
            fh.write(record.model_dump_json())
            fh.write("\n")

        return path
