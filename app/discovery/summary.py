from app.models.schemas import DiscoveryResult

class FinalSummary:
    def render(self, result: DiscoveryResult) -> str:
        lines = [
            "========================================",
            "FINAL REQUIREMENT FOR CLIENT APPROVAL",
            "========================================",
            "",
            f"Project Type: {result.project_type}",
            "",
            "Confirmed Requirements:"
        ]
        for item in result.confirmed:
            lines.append(f"- {item.key}: {item.value}")

        if result.internal_decisions:
            lines.extend(["", "Internal Technical Decisions:"])
            for item in result.internal_decisions:
                if item.key != "discovery_engine_version":
                    lines.append(f"- {item.key}: {item.value}")

        lines.extend([
            "",
            "No implementation may begin until the client explicitly approves this summary."
        ])
        return "\n".join(lines)
