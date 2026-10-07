from app.models.schemas import RequirementItem, DiscoveryResult

class ConfirmationGate:
    def can_final_approve(self, result: DiscoveryResult) -> bool:
        return (
            not any(x.blocking for x in result.inferred)
            and not any(x.blocking for x in result.unknown)
        )

    def promote_confirmed(self, result: DiscoveryResult, key: str, value, source: str = "client_confirmation"):
        confirmed = [x for x in result.confirmed if x.key != key]
        inferred = [x for x in result.inferred if x.key != key]
        proposed = [x for x in result.proposed if x.key != key]
        unknown = [x for x in result.unknown if x.key != key]

        confirmed.append(RequirementItem(
            key=key, value=value, status="CONFIRMED",
            source=source, blocking=False, confidence=1.0
        ))

        updated = result.model_copy(update={
            "confirmed": confirmed,
            "inferred": inferred,
            "proposed": proposed,
            "unknown": unknown,
        })
        updated = updated.model_copy(update={
            "ready_for_final_approval": self.can_final_approve(updated),
            "ready_for_development": self.can_final_approve(updated) and updated.client_approved
        })
        return updated

    def approve_final(self, result: DiscoveryResult):
        if not self.can_final_approve(result):
            return result
        return result.model_copy(update={
            "client_approved": True,
            "ready_for_final_approval": True,
            "ready_for_development": True
        })
