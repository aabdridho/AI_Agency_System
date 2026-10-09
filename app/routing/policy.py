from app.routing.goat_config import GoatConfig, GoatTierClassifier
from app.routing.models import RoutingDecision


class RoutingPolicy:
    @staticmethod
    def _risk_for(
        tier: str,
        category: str,
    ) -> str:
        if tier == "deep":
            return "high"

        if category in {
            "architecture",
            "qa",
        }:
            return "high"

        if tier in {
            "quick",
        }:
            return "low"

        return "medium"

    @staticmethod
    def _checks_for(
        tier: str,
        category: str,
    ) -> list[str]:
        if category == "qa":
            return [
                "tests",
                "typecheck",
                "lint",
                "review",
            ]

        if tier == "quick":
            return [
                "targeted_tests",
                "lint",
            ]

        if tier == "deep":
            return [
                "tests",
                "typecheck",
                "lint",
                "review",
            ]

        if category == "frontend":
            return [
                "tests",
                "typecheck",
                "lint",
            ]

        return [
            "tests",
            "lint",
        ]

    """
    V0.13 GOAT routing policy.

    Responsibility split:

    1. Category/classifier describes the task domain.
    2. GOAT tier classifier chooses required capability.
    3. Runtime GOAT config chooses provider/model/effort.
    4. Execution executes that explicit resolved contract.

    Invariants:
    - one task = one primary model
    - deterministic QA stays deterministic first
    - no automatic second-model review
    - fallback/escalation is bounded to one step
    """

    def __init__(
        self,
        goat_config: GoatConfig | None = None,
        tier_classifier: GoatTierClassifier | None = None,
    ):
        self.goat_config = goat_config or GoatConfig()
        self.tier_classifier = tier_classifier or GoatTierClassifier()

    def decide(
        self,
        task_id: str,
        task_text: str,
        category: str,
        confidence: float,
    ) -> RoutingDecision:
        tier = self.tier_classifier.classify(
            task_text,
            category,
        )

        primary = self.goat_config.resolve_for_task(
            tier,
            category,
        )

        escalation = self.goat_config.resolve_escalation(
            primary.owner,
        )

        risk = self._risk_for(
            tier,
            category,
        )

        checks = self._checks_for(
            tier,
            category,
        )

        # QA stays zero-token/deterministic first.
        # Because deterministic QA has no provider family, remediation uses
        # the canonical escalation tier rather than cross-provider inversion.
        if category == "qa":
            escalation = self.goat_config.resolve("esc")

            return RoutingDecision(
                task_id=task_id,
                task_text=task_text,
                category=category,
                goat_tier="review",
                route="review",
                risk=risk,
                checks=checks,
                triage_mode="rules",
                verifier="deterministic_qa",
                primary_owner="deterministic_qa",
                primary_model=None,
                primary_effort=None,
                fallback_owner=escalation.owner,
                fallback_model=escalation.executable_model,
                fallback_effort=escalation.effort,
                model_source=primary.source,
                confidence=confidence,
                reason=(
                    "Deterministic QA runs first. AI escalation is used only "
                    "when deterministic validation fails and remediation is required."
                ),
                escalation_trigger=(
                    "Escalate only after a reproducible deterministic QA failure."
                ),
                max_escalations=1,
            )

        # Triage itself is handled internally before execution, so an
        # implementation task may not resolve to rules.
        if primary.owner == "internal_decision":
            primary = self.goat_config.resolve("build")
            tier = "build"

        fallback_owner = escalation.owner

        # Avoid pretending there is a useful fallback if escalation resolves
        # to the exact same owner/model/effort contract.
        same_execution = (
            fallback_owner == primary.owner
            and escalation.executable_model == primary.executable_model
            and escalation.effort == primary.effort
        )

        return RoutingDecision(
            task_id=task_id,
            task_text=task_text,
            category=category,
            goat_tier=tier,
            route=tier,
            risk=risk,
            checks=checks,
            triage_mode="rules",
            verifier="deterministic_qa",
            primary_owner=primary.owner,
            primary_model=primary.executable_model,
            primary_effort=primary.effort,
            fallback_owner=None if same_execution else fallback_owner,
            fallback_model=(
                None
                if same_execution
                else escalation.executable_model
            ),
            fallback_effort=(
                None
                if same_execution
                else escalation.effort
            ),
            model_source=primary.source,
            confidence=confidence,
            reason=(
                f"GOAT tier '{tier}' resolved through runtime model config "
                f"to owner '{primary.owner}' and model "
                f"'{primary.executable_model}'."
            ),
            escalation_trigger=(
                "Escalate once only after explicit execution failure, "
                "no-change failure, or blocking integration failure."
            ),
            max_escalations=0 if same_execution else 1,
        )
