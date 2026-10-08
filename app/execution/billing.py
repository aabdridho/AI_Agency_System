from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from pydantic import BaseModel, Field

from app.execution.costs import ProjectCostSummary


ZERO = Decimal("0")
HUNDRED = Decimal("100")


def money(value: Decimal) -> str:
    return str(
        value.quantize(
            Decimal("0.000000001"),
            rounding=ROUND_HALF_UP,
        )
    )


def dec(value: str | int | float | Decimal) -> Decimal:
    return Decimal(str(value))


class BillingPolicy(BaseModel):
    currency: str = "USD"

    infrastructure_allocation_usd: str = "0"
    subscription_allocation_usd: str = "0"
    engineering_service_fee_usd: str = "0"

    qa_risk_overhead_percent: str = "0"
    margin_percent: str = "0"

    minimum_project_fee_usd: str = "0"

    pricing_basis: str = (
        "ai_compute_equivalent_list_reference"
    )


class BillingBreakdown(BaseModel):
    project_name: str
    currency: str

    ai_compute_reference_usd: str

    # Actual provider cash charge remains separate.
    actual_provider_cash_cost_usd: str | None = None
    actual_provider_cost_known: bool = False

    infrastructure_allocation_usd: str
    subscription_allocation_usd: str
    engineering_service_fee_usd: str

    commercial_base_usd: str

    qa_risk_overhead_percent: str
    qa_risk_overhead_usd: str

    margin_percent: str
    margin_usd: str

    calculated_client_price_usd: str
    minimum_project_fee_usd: str
    final_client_price_usd: str

    pricing_basis: str

    ai_cost_complete: bool
    billing_complete: bool

    note: str


class BillingEngine:
    def calculate(
        self,
        cost_summary: ProjectCostSummary,
        policy: BillingPolicy,
    ) -> BillingBreakdown:
        ai_reference = dec(
            cost_summary.known_equivalent_cost_usd
        )

        infra = dec(
            policy.infrastructure_allocation_usd
        )

        subscription = dec(
            policy.subscription_allocation_usd
        )

        engineering = dec(
            policy.engineering_service_fee_usd
        )

        qa_pct = dec(
            policy.qa_risk_overhead_percent
        )

        margin_pct = dec(
            policy.margin_percent
        )

        minimum_fee = dec(
            policy.minimum_project_fee_usd
        )

        for name, value in (
            ("infrastructure_allocation_usd", infra),
            ("subscription_allocation_usd", subscription),
            ("engineering_service_fee_usd", engineering),
            ("qa_risk_overhead_percent", qa_pct),
            ("margin_percent", margin_pct),
            ("minimum_project_fee_usd", minimum_fee),
        ):
            if value < ZERO:
                raise ValueError(
                    f"{name} must not be negative."
                )

        commercial_base = (
            ai_reference
            + infra
            + subscription
            + engineering
        )

        qa_overhead = (
            commercial_base
            * qa_pct
            / HUNDRED
        )

        before_margin = (
            commercial_base
            + qa_overhead
        )

        margin = (
            before_margin
            * margin_pct
            / HUNDRED
        )

        calculated_price = (
            before_margin
            + margin
        )

        final_price = max(
            calculated_price,
            minimum_fee,
        )

        actual_cash = (
            cost_summary.actual_cash_cost_usd
        )

        actual_known = (
            actual_cash is not None
        )

        return BillingBreakdown(
            project_name=cost_summary.project_name,
            currency=policy.currency,

            ai_compute_reference_usd=money(
                ai_reference
            ),

            actual_provider_cash_cost_usd=actual_cash,
            actual_provider_cost_known=actual_known,

            infrastructure_allocation_usd=money(
                infra
            ),

            subscription_allocation_usd=money(
                subscription
            ),

            engineering_service_fee_usd=money(
                engineering
            ),

            commercial_base_usd=money(
                commercial_base
            ),

            qa_risk_overhead_percent=money(
                qa_pct
            ),

            qa_risk_overhead_usd=money(
                qa_overhead
            ),

            margin_percent=money(
                margin_pct
            ),

            margin_usd=money(
                margin
            ),

            calculated_client_price_usd=money(
                calculated_price
            ),

            minimum_project_fee_usd=money(
                minimum_fee
            ),

            final_client_price_usd=money(
                final_price
            ),

            pricing_basis=policy.pricing_basis,

            ai_cost_complete=cost_summary.is_complete,

            billing_complete=cost_summary.is_complete,

            note=(
                "AI compute uses equivalent/list pricing as a "
                "commercial reference unless actual provider cash "
                "billing evidence is available. Client price is a "
                "commercial amount, not a claim about actual provider "
                "cash cost."
            ),
        )


class BillingConfig:
    def __init__(
        self,
        path: str | Path = (
            Path("runtime_data")
            / "config"
            / "billing.json"
        ),
    ):
        self.path = Path(path)

    def load(self) -> BillingPolicy:
        if not self.path.exists():
            return BillingPolicy()

        raw = json.loads(
            self.path.read_text(
                encoding="utf-8-sig"
            )
        )

        return BillingPolicy.model_validate(raw)

    def save(
        self,
        policy: BillingPolicy,
    ) -> Path:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.path.write_text(
            policy.model_dump_json(indent=2),
            encoding="utf-8",
        )

        return self.path


def load_cost_summary(
    path: str | Path,
) -> ProjectCostSummary:
    return ProjectCostSummary.model_validate_json(
        Path(path).read_text(
            encoding="utf-8"
        )
    )


def write_project_billing_summary(
    usage_root: str | Path,
    project_name: str,
    *,
    policy: BillingPolicy | None = None,
    config: BillingConfig | None = None,
) -> BillingBreakdown:
    root = Path(usage_root)
    project_dir = root / project_name

    cost_path = (
        project_dir
        / "cost_summary.json"
    )

    if not cost_path.exists():
        raise FileNotFoundError(
            f"Cost summary not found: {cost_path}"
        )

    cost_summary = load_cost_summary(
        cost_path
    )

    config = config or BillingConfig()

    if policy is None:
        policy = config.load()

    result = BillingEngine().calculate(
        cost_summary,
        policy,
    )

    output = (
        project_dir
        / "billing_summary.json"
    )

    output.write_text(
        result.model_dump_json(indent=2),
        encoding="utf-8",
    )

    return result
