from __future__ import annotations
import json
from pathlib import Path

class DeploymentGuardError(RuntimeError):
    pass

class DeploymentGuard:
    def __init__(self, delivery_report_path):
        self.delivery_report_path = Path(delivery_report_path)

    def validate(self):
        if not self.delivery_report_path.exists():
            raise DeploymentGuardError("Delivery report is missing. Run V0.8 readiness first.")
        data = json.loads(self.delivery_report_path.read_text(encoding="utf-8", errors="replace"))
        if data.get("overall_status") != "ready":
            raise DeploymentGuardError(
                f"Delivery status is {data.get('overall_status')!r}, not 'ready'. Resolve delivery blockers before deployment."
            )
        if any(c.get("status") == "blocker" for c in (data.get("checks") or [])):
            raise DeploymentGuardError("Delivery report still contains blocker checks.")
        return data
