from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from pydantic import BaseModel

from app.execution.costs import (
    CostEngine,
    PRICE_REGISTRY,
    load_usage_records,
)
from app.execution.usage import UsageRecord
from app.routing.goat_config import GoatConfig


ZERO = Decimal("0")


def money(value: Decimal) -> str:
    return str(
        value.quantize(
            Decimal("0.000000001"),
            rounding=ROUND_HALF_UP,
        )
    )


def percent(value: Decimal) -> str:
    return str(
        value.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
    )


class SavingsRecord(BaseModel):
    task_id: str
    phase: str

    goat_tier: str | None = None
    actual_model: str | None = None
    baseline_model: str | None = None

    goat_equivalent_cost_usd: str | None = None
    baseline_equivalent_cost_usd: str | None = None

    estimated_equivalent_savings_usd: str | None = None
    estimated_savings_percent: str | None = None

    complete: bool
    estimated: bool = True
    reason: str | None = None


class GoatSavingsSummary(BaseModel):
    project_name: str

    baseline_strategy: str
    baseline_tier: str
    baseline_model: str | None

    observed_records: int
    comparable_records: int
    unknown_records: int

    goat_known_equivalent_cost_usd: str
    baseline_known_equivalent_cost_usd: str

    estimated_equivalent_savings_usd: str
    estimated_savings_percent: str | None

    is_complete: bool
    estimated: bool = True

    methodology: str

    records: list[SavingsRecord]


class GoatSavingsEngine:
    """
    Counterfactual GOAT savings estimator.

    Baseline strategy:
        price each observed usage record using the current GOAT escalation
        model while preserving the OBSERVED token quantities.

    This is intentionally called an estimate:
    a different model can tokenize/generate differently in a real execution.
    """

    def __init__(
        self,
        goat_config: GoatConfig | None = None,
        cost_engine: CostEngine | None = None,
    ):
        self.goat_config = goat_config or GoatConfig()
        self.cost_engine = cost_engine or CostEngine()

    def _baseline_model(self) -> tuple[str | None, str | None]:
        resolved = self.goat_config.resolve("esc")
        return resolved.executable_model, resolved.owner

    def _reprice_record(
        self,
        record: UsageRecord,
        baseline_model: str,
    ):
        rate = PRICE_REGISTRY.get(baseline_model)

        if rate is None:
            return None, (
                f"Baseline model '{baseline_model}' has no verified "
                "price registry entry."
            )

        metrics = record.metrics.model_copy(
            update={
                "provider": rate["provider"],
                "model": baseline_model,

                # Provider-reported cost belongs to the actually executed
                # model and must never leak into the counterfactual.
                "provider_reported_cost_usd": None,
                "cost_basis": None,

                "model_source": "goat_savings_baseline",
            }
        )

        synthetic = record.model_copy(
            update={"metrics": metrics}
        )

        result = self.cost_engine.calculate(synthetic)

        if not result.complete:
            return None, result.reason

        return result, None

    def calculate_record(
        self,
        record: UsageRecord,
        baseline_model: str,
    ) -> SavingsRecord:
        actual = self.cost_engine.calculate(record)

        if not actual.complete or actual.equivalent_cost_usd is None:
            return SavingsRecord(
                task_id=record.task_id,
                phase=record.phase,
                goat_tier=record.metrics.goat_tier,
                actual_model=record.metrics.model,
                baseline_model=baseline_model,
                complete=False,
                reason=(
                    actual.reason
                    or "Actual GOAT record could not be priced."
                ),
            )

        baseline, reason = self._reprice_record(
            record,
            baseline_model,
        )

        if baseline is None or baseline.equivalent_cost_usd is None:
            return SavingsRecord(
                task_id=record.task_id,
                phase=record.phase,
                goat_tier=record.metrics.goat_tier,
                actual_model=record.metrics.model,
                baseline_model=baseline_model,
                goat_equivalent_cost_usd=actual.equivalent_cost_usd,
                complete=False,
                reason=reason,
            )

        actual_cost = Decimal(actual.equivalent_cost_usd)
        baseline_cost = Decimal(baseline.equivalent_cost_usd)

        saving = baseline_cost - actual_cost

        pct = None
        if baseline_cost > ZERO:
            pct = (
                saving
                / baseline_cost
                * Decimal("100")
            )

        return SavingsRecord(
            task_id=record.task_id,
            phase=record.phase,
            goat_tier=record.metrics.goat_tier,
            actual_model=record.metrics.model,
            baseline_model=baseline_model,
            goat_equivalent_cost_usd=money(actual_cost),
            baseline_equivalent_cost_usd=money(baseline_cost),
            estimated_equivalent_savings_usd=money(saving),
            estimated_savings_percent=(
                percent(pct)
                if pct is not None
                else None
            ),
            complete=True,
            estimated=True,
        )

    def summarize(
        self,
        project_name: str,
        records: list[UsageRecord],
    ) -> GoatSavingsSummary:
        baseline_model, _ = self._baseline_model()

        if not baseline_model:
            return GoatSavingsSummary(
                project_name=project_name,
                baseline_strategy="current_escalation_tier_same_observed_tokens",
                baseline_tier="esc",
                baseline_model=None,
                observed_records=len(records),
                comparable_records=0,
                unknown_records=len(records),
                goat_known_equivalent_cost_usd=money(ZERO),
                baseline_known_equivalent_cost_usd=money(ZERO),
                estimated_equivalent_savings_usd=money(ZERO),
                estimated_savings_percent=None,
                is_complete=False,
                estimated=True,
                methodology=(
                    "No executable escalation model is configured."
                ),
                records=[],
            )

        calculated = [
            self.calculate_record(r, baseline_model)
            for r in records
        ]

        comparable = [
            r for r in calculated
            if r.complete
        ]

        goat_total = sum(
            (
                Decimal(r.goat_equivalent_cost_usd)
                for r in comparable
                if r.goat_equivalent_cost_usd is not None
            ),
            ZERO,
        )

        baseline_total = sum(
            (
                Decimal(r.baseline_equivalent_cost_usd)
                for r in comparable
                if r.baseline_equivalent_cost_usd is not None
            ),
            ZERO,
        )

        saving_total = baseline_total - goat_total

        pct = None
        if baseline_total > ZERO:
            pct = (
                saving_total
                / baseline_total
                * Decimal("100")
            )

        unknown = len(calculated) - len(comparable)

        return GoatSavingsSummary(
            project_name=project_name,
            baseline_strategy="current_escalation_tier_same_observed_tokens",
            baseline_tier="esc",
            baseline_model=baseline_model,
            observed_records=len(calculated),
            comparable_records=len(comparable),
            unknown_records=unknown,
            goat_known_equivalent_cost_usd=money(goat_total),
            baseline_known_equivalent_cost_usd=money(baseline_total),
            estimated_equivalent_savings_usd=money(saving_total),
            estimated_savings_percent=(
                percent(pct)
                if pct is not None
                else None
            ),
            is_complete=unknown == 0,
            estimated=True,
            methodology=(
                "Counterfactual list-price estimate. Each actually observed "
                "usage record is repriced using the current GOAT escalation "
                "model while preserving the observed token quantities. "
                "It is not an actual provider charge or guaranteed cash saving; "
                "a different model may produce a different token volume."
            ),
            records=calculated,
        )


def write_project_savings_summary(
    usage_root: str | Path,
    project_name: str,
    *,
    goat_config: GoatConfig | None = None,
) -> GoatSavingsSummary:
    root = Path(usage_root)
    project_dir = root / project_name

    records = load_usage_records(
        project_dir / "usage.jsonl"
    )

    summary = GoatSavingsEngine(
        goat_config=goat_config
    ).summarize(
        project_name,
        records,
    )

    project_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = project_dir / "savings_summary.json"

    output.write_text(
        summary.model_dump_json(indent=2),
        encoding="utf-8",
    )

    return summary
