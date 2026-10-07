from pathlib import Path
from app.models.schemas import DiscoveryResult

class RequirementDocumentGenerator:
    def render(self, result: DiscoveryResult) -> str:
        lines = [
            "# Project Requirements", "",
            "## Status",
            "CLIENT_APPROVED" if result.client_approved else "DRAFT", "",
            "## Project Type", result.project_type, "",
            "## Confirmed Requirements"
        ]

        for item in result.confirmed:
            lines.append(f"- **{item.key}**: {item.value}")

        tech_items = [x for x in result.internal_decisions if x.key != "discovery_engine_version"]
        if tech_items:
            lines += ["", "## Internal Technical Decisions"]
            for item in tech_items:
                lines.append(f"- **{item.key}**: {item.value}")

        lines += [
            "", "## Audit Note",
            f"- Client approved: {result.client_approved}",
            "- Implementation must follow confirmed requirements only.",
            "- Revisions must update affected documentation before implementation.",
            ""
        ]
        return "\n".join(lines)

    def save(self, result: DiscoveryResult, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.render(result), encoding="utf-8")
        return target
