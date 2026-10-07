from app.models.schemas import RequirementItem

class ReferenceAnalyzer:
    def analyze(self, prompt: str, references: list[str]):
        confirmed = []
        inferred = []
        unknown = []

        if not references:
            return confirmed, inferred, unknown

        confirmed.append(
            RequirementItem(
                key="reference_urls",
                value=references,
                status="CONFIRMED",
                source="client_reference",
                blocking=False,
                confidence=1.0,
            )
        )

        p = prompt.lower()
        preferences = []
        if "layout" in p:
            preferences.append("layout")
        if "animasi" in p or "animation" in p:
            preferences.append("animation")
        if "typography" in p or "tipografi" in p:
            preferences.append("typography")
        if "warna" in p or "color" in p:
            preferences.append("color")
        if "spacing" in p:
            preferences.append("spacing")

        if preferences:
            confirmed.append(
                RequirementItem(
                    key="reference_preferences",
                    value=sorted(set(preferences)),
                    status="CONFIRMED",
                    source="client_prompt",
                    blocking=False,
                    confidence=1.0,
                )
            )
        else:
            unknown.append(
                RequirementItem(
                    key="reference_preferences",
                    value=None,
                    status="UNKNOWN",
                    source="reference_analyzer",
                    blocking=True,
                    confidence=None,
                )
            )

        return confirmed, inferred, unknown
