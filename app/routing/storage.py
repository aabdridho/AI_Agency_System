import json
from pathlib import Path
from app.routing.models import RoutingPlan

class RoutingStorage:
    """
    Stores operational routing artifacts OUTSIDE client project directories.
    """

    def save(self, plan: RoutingPlan, runtime_root: str | Path) -> Path:
        runtime_root = Path(runtime_root)
        target = runtime_root / "routing" / plan.project_name / "routing_plan.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(plan.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return target
