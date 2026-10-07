from collections import Counter
from app.routing.models import RoutingPlan

class RoutingSummary:
    def render(self, plan: RoutingPlan) -> str:
        counts = Counter(d.primary_owner for d in plan.decisions)
        lines = [
            "=" * 72,
            "ROUTING PLAN",
            "=" * 72,
            f"Project: {plan.project_name}",
            f"Source: {plan.source_task_file}",
            "",
        ]

        for d in plan.decisions:
            lines += [
                f"[{d.task_id}] {d.task_text}",
                f"  category : {d.category}",
                f"  primary  : {d.primary_owner}",
                f"  fallback : {d.fallback_owner or '-'}",
                f"  confidence: {d.confidence:.2f}",
                f"  reason   : {d.reason}",
                "",
            ]

        lines += ["Owner Summary:"]
        for owner, count in sorted(counts.items()):
            lines.append(f"- {owner}: {count}")

        lines += [
            "",
            "Policy:",
            "- One task has one primary owner.",
            "- No automatic second-model review.",
            "- Deterministic QA runs before AI diagnosis.",
            "- Fallback/escalation is bounded to one step.",
            "",
        ]
        return "\n".join(lines)
