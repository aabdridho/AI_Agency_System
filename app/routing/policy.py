from app.routing.models import RoutingDecision

class RoutingPolicy:
    """
    Deterministic V0.5 routing policy.

    Design goals:
    - one task = one primary owner
    - no automatic dual-model review
    - deterministic QA before AI review
    - fallback only on explicit failure/risk trigger
    - max escalation = 1
    """

    def decide(self, task_id: str, task_text: str, category: str, confidence: float) -> RoutingDecision:
        if category == "frontend":
            return RoutingDecision(
                task_id=task_id,
                task_text=task_text,
                category=category,
                primary_owner="claude_code",
                fallback_owner="codex",
                confidence=confidence,
                reason="Frontend/UI-heavy work is assigned to Claude Code as the primary owner.",
                escalation_trigger=(
                    "Escalate only if implementation fails deterministic checks, "
                    "produces blocking integration issues, or Claude Code cannot complete the task."
                ),
            )

        if category == "backend":
            return RoutingDecision(
                task_id=task_id,
                task_text=task_text,
                category=category,
                primary_owner="codex",
                fallback_owner="claude_code",
                confidence=confidence,
                reason="Backend/server/data-flow work is assigned to Codex as the primary owner.",
                escalation_trigger=(
                    "Escalate only after reproducible failure, blocking integration error, "
                    "or unresolved implementation issue."
                ),
            )

        if category == "architecture":
            return RoutingDecision(
                task_id=task_id,
                task_text=task_text,
                category=category,
                primary_owner="claude_code",
                fallback_owner="codex",
                confidence=confidence,
                reason="Architecture is assigned to Claude Code first, with Codex as bounded fallback.",
                escalation_trigger=(
                    "Escalate if the architecture conflicts with confirmed requirements "
                    "or deterministic repository constraints."
                ),
            )

        if category == "qa":
            return RoutingDecision(
                task_id=task_id,
                task_text=task_text,
                category=category,
                primary_owner="deterministic_qa",
                fallback_owner="codex",
                confidence=confidence,
                reason="QA must run deterministic tools first; AI is used only when checks fail or diagnosis is needed.",
                escalation_trigger="Use Codex only when deterministic checks fail and diagnosis/remediation is required.",
            )

        if category == "setup":
            return RoutingDecision(
                task_id=task_id,
                task_text=task_text,
                category=category,
                primary_owner="codex",
                fallback_owner="claude_code",
                confidence=confidence,
                reason="Project setup is treated as engineering/tooling work and routed to Codex first.",
                escalation_trigger="Escalate only if setup conflicts with frontend-specific tooling or cannot be completed.",
            )

        return RoutingDecision(
            task_id=task_id,
            task_text=task_text,
            category=category,
            primary_owner="codex",
            fallback_owner="claude_code",
            confidence=confidence,
            reason="General engineering defaults to Codex under the V0.5 policy.",
            escalation_trigger="Escalate only on reproducible failure or clear domain mismatch.",
        )
