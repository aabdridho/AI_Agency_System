from app.models.schemas import RequirementItem

class DependencyExpander:
    def expand(self, confirmed: list[RequirementItem]) -> list[RequirementItem]:
        existing = {x.key for x in confirmed}
        by_key = {x.key: x for x in confirmed}
        additions = []

        contact = by_key.get("contact_behavior")
        if contact and contact.value == "contact_form":
            if "contact_destination" not in existing:
                additions.append(RequirementItem(
                    key="contact_destination",
                    value=None,
                    status="UNKNOWN",
                    source="dependency_expander",
                    blocking=True
                ))
            if "contact_fields" not in existing:
                additions.append(RequirementItem(
                    key="contact_fields",
                    value=None,
                    status="UNKNOWN",
                    source="dependency_expander",
                    blocking=True
                ))

        return additions
