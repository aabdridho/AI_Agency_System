from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from pydantic import BaseModel

from app.execution.usage import UsageMetrics, UsageRecord


MILLION = Decimal("1000000")
ZERO = Decimal("0")

PRICING_VERSION = "2026-10-09"

# Standard list prices, USD per 1M tokens.
#
# IMPORTANT:
# These are model-equivalent/list prices, not proof of actual cash charged
# to the account running ChatGPT/Codex/Claude subscriptions.
PRICE_REGISTRY = {
    "gpt-6-luna": {
        "provider": "openai",
        "input": Decimal("0.10"),
        "cached_input": Decimal("0.01"),
        "cache_write": Decimal("0.125"),
        "output": Decimal("0.50"),
        "source": "openai_standard_list",
    },
    "gpt-6.1-sol": {
        "provider": "openai",
        "input": Decimal("2.00"),
        "cached_input": Decimal("0.10"),
        "cache_write": Decimal("2.50"),
        "output": Decimal("10.00"),
        "source": "openai_standard_list",
    },
    "gpt-6-astra": {
        "provider": "openai",
        "input": Decimal("10.00"),
        "cached_input": Decimal("1.00"),
        "cache_write": Decimal("12.50"),
        "output": Decimal("50.00"),
        "source": "openai_standard_list",
    },

    # Only exact canonical Claude models are priced here.
    # Do NOT price generic aliases such as "sonnet" or "opus".
    "claude-sonnet-5-5": {
        "provider": "anthropic",
        "input": Decimal("2.00"),
        "cached_input": Decimal("0.10"),
        "cache_write": Decimal("2.50"),
        "output": Decimal("10.00"),
        "source": "anthropic_standard_list_2026_10_07",
    },
    "claude-opus-5-5": {
        "provider": "anthropic",
        "input": Decimal("4.00"),
        "cached_input": Decimal("0.20"),
        "cache_write": Decimal("5.00"),
        "output": Decimal("20.00"),
        "source": "anthropic_standard_list",
    },
}


def money(value: Decimal) -> str:
    return str(
        value.quantize(
            Decimal("0.000000001"),
            rounding=ROUND_HALF_UP,
        )
    )


class CostBreakdown(BaseModel):
    project_name: str
    task_id: str
    owner: str
    phase: str

    provider: str
    model: str | None
    goat_tier: str | None = None
    requested_effort: str | None = None

    equivalent_cost_usd: str | None = None

    # Deliberately null for now.
    # Actual account charge requires provider billing/invoice evidence.
    actual_cash_cost_usd: str | None = None

    cost_basis: str
    pricing_source: str | None = None
    pricing_version: str = PRICING_VERSION

    input_cost_usd: str | None = None
    cached_input_cost_usd: str | None = None
    cache_write_cost_usd: str | None = None
    output_cost_usd: str | None = None

    complete: bool
    reason: str | None = None


class ProjectCostSummary(BaseModel):
    project_name: str
    pricing_version: str = PRICING_VERSION

    total_records: int
    priced_records: int
    unknown_records: int

    known_equivalent_cost_usd: str

    # Must stay null until actual provider cash/billing evidence exists.
    actual_cash_cost_usd: str | None = None

    is_complete: bool
    records: list[CostBreakdown]


class CostEngine:
    def calculate(
        self,
        record: UsageRecord,
    ) -> CostBreakdown:
        m = record.metrics

        # ---------------------------------------------------------
        # 1. Provider-reported LIST cost wins when explicitly marked
        #    as list pricing.
        # ---------------------------------------------------------
        if (
            m.provider_reported_cost_usd is not None
            and m.cost_basis == "list"
        ):
            value = Decimal(str(m.provider_reported_cost_usd))

            return CostBreakdown(
                project_name=record.project_name,
                task_id=record.task_id,
                owner=record.owner,
                phase=record.phase,
                provider=m.provider,
                model=m.model,
                goat_tier=m.goat_tier,
                requested_effort=m.requested_effort,
                equivalent_cost_usd=money(value),
                actual_cash_cost_usd=None,
                cost_basis="provider_reported_list",
                pricing_source=f"{m.provider}_cli_reported",
                complete=True,
            )

        # Never silently reinterpret a provider-reported non-list cost.
        if (
            m.provider_reported_cost_usd is not None
            and m.cost_basis not in (None, "list")
        ):
            return self._unknown(
                record,
                reason=(
                    "Provider reported a cost but its basis is not an "
                    "explicit supported list-cost basis."
                ),
            )

        # ---------------------------------------------------------
        # 2. Calculated equivalent list cost.
        # ---------------------------------------------------------
        if not m.model:
            return self._unknown(
                record,
                reason="Model is unknown; pricing must not be guessed.",
            )

        rate = PRICE_REGISTRY.get(m.model)
        if rate is None:
            return self._unknown(
                record,
                reason=(
                    f"No verified price registry entry for model "
                    f"'{m.model}'."
                ),
            )

        if rate["provider"] != m.provider:
            return self._unknown(
                record,
                reason=(
                    "Usage provider does not match pricing registry "
                    "provider."
                ),
            )

        if m.provider == "openai":
            return self._calculate_openai(record, rate)

        if m.provider == "anthropic":
            return self._calculate_anthropic(record, rate)

        return self._unknown(
            record,
            reason=f"Unsupported provider '{m.provider}'.",
        )

    def _calculate_openai(
        self,
        record: UsageRecord,
        rate: dict,
    ) -> CostBreakdown:
        m = record.metrics

        # OpenAI input_tokens includes cached/cache-write token details.
        uncached = (
            m.input_tokens
            - m.cached_input_tokens
            - m.cache_write_input_tokens
        )

        if uncached < 0:
            return self._unknown(
                record,
                reason=(
                    "OpenAI token breakdown is inconsistent: cached/cache "
                    "write tokens exceed total input tokens."
                ),
            )

        input_cost = (
            Decimal(uncached)
            * rate["input"]
            / MILLION
        )

        cached_cost = (
            Decimal(m.cached_input_tokens)
            * rate["cached_input"]
            / MILLION
        )

        cache_write_cost = (
            Decimal(m.cache_write_input_tokens)
            * rate["cache_write"]
            / MILLION
        )

        # reasoning_output_tokens is a DETAIL/SUBSET of output_tokens.
        # Never add it again here.
        output_cost = (
            Decimal(m.output_tokens)
            * rate["output"]
            / MILLION
        )

        total = (
            input_cost
            + cached_cost
            + cache_write_cost
            + output_cost
        )

        return CostBreakdown(
            project_name=record.project_name,
            task_id=record.task_id,
            owner=record.owner,
            phase=record.phase,
            provider=m.provider,
            model=m.model,
            goat_tier=m.goat_tier,
            requested_effort=m.requested_effort,
            equivalent_cost_usd=money(total),
            actual_cash_cost_usd=None,
            cost_basis="calculated_standard_list",
            pricing_source=rate["source"],
            input_cost_usd=money(input_cost),
            cached_input_cost_usd=money(cached_cost),
            cache_write_cost_usd=money(cache_write_cost),
            output_cost_usd=money(output_cost),
            complete=True,
        )

    def _calculate_anthropic(
        self,
        record: UsageRecord,
        rate: dict,
    ) -> CostBreakdown:
        m = record.metrics

        # Claude CLI modelUsage reports these buckets separately:
        # inputTokens, cacheReadInputTokens,
        # cacheCreationInputTokens, outputTokens.
        input_cost = (
            Decimal(m.input_tokens)
            * rate["input"]
            / MILLION
        )

        cached_cost = (
            Decimal(m.cached_input_tokens)
            * rate["cached_input"]
            / MILLION
        )

        cache_write_cost = (
            Decimal(m.cache_write_input_tokens)
            * rate["cache_write"]
            / MILLION
        )

        output_cost = (
            Decimal(m.output_tokens)
            * rate["output"]
            / MILLION
        )

        total = (
            input_cost
            + cached_cost
            + cache_write_cost
            + output_cost
        )

        return CostBreakdown(
            project_name=record.project_name,
            task_id=record.task_id,
            owner=record.owner,
            phase=record.phase,
            provider=m.provider,
            model=m.model,
            goat_tier=m.goat_tier,
            requested_effort=m.requested_effort,
            equivalent_cost_usd=money(total),
            actual_cash_cost_usd=None,
            cost_basis="calculated_standard_list",
            pricing_source=rate["source"],
            input_cost_usd=money(input_cost),
            cached_input_cost_usd=money(cached_cost),
            cache_write_cost_usd=money(cache_write_cost),
            output_cost_usd=money(output_cost),
            complete=True,
        )

    def _unknown(
        self,
        record: UsageRecord,
        *,
        reason: str,
    ) -> CostBreakdown:
        m = record.metrics

        return CostBreakdown(
            project_name=record.project_name,
            task_id=record.task_id,
            owner=record.owner,
            phase=record.phase,
            provider=m.provider,
            model=m.model,
            goat_tier=m.goat_tier,
            requested_effort=m.requested_effort,
            equivalent_cost_usd=None,
            actual_cash_cost_usd=None,
            cost_basis="unknown",
            pricing_source=None,
            complete=False,
            reason=reason,
        )

    def summarize(
        self,
        project_name: str,
        records: list[UsageRecord],
    ) -> ProjectCostSummary:
        calculated = [self.calculate(r) for r in records]

        known = [
            r for r in calculated
            if r.equivalent_cost_usd is not None
        ]

        total = sum(
            (
                Decimal(r.equivalent_cost_usd)
                for r in known
            ),
            ZERO,
        )

        unknown = len(calculated) - len(known)

        return ProjectCostSummary(
            project_name=project_name,
            total_records=len(calculated),
            priced_records=len(known),
            unknown_records=unknown,
            known_equivalent_cost_usd=money(total),
            actual_cash_cost_usd=None,
            is_complete=unknown == 0,
            records=calculated,
        )


def load_usage_records(
    usage_file: str | Path,
) -> list[UsageRecord]:
    path = Path(usage_file)

    if not path.exists():
        return []

    records: list[UsageRecord] = []

    for raw in path.read_text(
        encoding="utf-8"
    ).splitlines():
        raw = raw.strip()

        if not raw:
            continue

        records.append(
            UsageRecord.model_validate_json(raw)
        )

    return records


def write_project_cost_summary(
    usage_root: str | Path,
    project_name: str,
) -> ProjectCostSummary:
    root = Path(usage_root)
    project_dir = root / project_name

    usage_file = project_dir / "usage.jsonl"

    records = load_usage_records(usage_file)

    summary = CostEngine().summarize(
        project_name,
        records,
    )

    project_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = project_dir / "cost_summary.json"

    output.write_text(
        summary.model_dump_json(indent=2),
        encoding="utf-8",
    )

    return summary
