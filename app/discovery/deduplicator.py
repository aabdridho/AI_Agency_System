from app.models.schemas import RequirementItem

class SemanticDeduplicator:
    def clean_confirmed(self, confirmed: list[RequirementItem]) -> list[RequirementItem]:
        sections = set()
        for item in confirmed:
            if item.key == "required_sections" and isinstance(item.value, list):
                sections.update(item.value)

        cleaned = []
        for item in confirmed:
            if item.key == "contact" and "contact" in sections:
                continue
            if item.key == "portfolio_projects" and "projects" in sections:
                continue
            cleaned.append(item)

        return cleaned
