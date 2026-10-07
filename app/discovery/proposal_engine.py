from app.models.schemas import RequirementItem

PORTFOLIO_PROPOSALS = [
    ("hero", "Hero section"),
    ("skills", "Skills section"),
    ("experience", "Experience section"),
]

class ProposalEngine:
    def build(self, project_type: str, confirmed_keys: set[str], confirmed_sections: set[str], prompt: str):
        proposals = []
        allow_proposals = any(
            phrase in prompt.lower()
            for phrase in [
                "sisanya bisa dikembangkan",
                "bisa dikembangkan sesuai pasaran",
                "boleh dikembangkan",
                "boleh kasih saran",
                "tambahkan yang cocok",
                "bebas kasih saran",
                "bebas kasih rekomendasi",
                "sisanya bebas",
            ]
        )

        if not allow_proposals:
            return proposals

        if project_type == "portfolio":
            for key, label in PORTFOLIO_PROPOSALS:
                if key not in confirmed_sections:
                    proposals.append(RequirementItem(
                        key=f"section_{key}",
                        value=label,
                        status="PROPOSED",
                        source="system_proposal",
                        blocking=False,
                        confidence=0.8
                    ))

        return proposals
