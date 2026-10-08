from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.orchestration.models import OrchestrationState


class OrchestrationStateStore:
    def __init__(
        self,
        runtime_root: str | Path = "runtime_data",
    ):
        self.runtime_root = Path(runtime_root)

    def path_for(
        self,
        project_name: str,
    ) -> Path:
        return (
            self.runtime_root
            / "orchestration"
            / project_name
            / "state.json"
        )

    def exists(
        self,
        project_name: str,
    ) -> bool:
        return self.path_for(project_name).is_file()

    def load(
        self,
        project_name: str,
    ) -> OrchestrationState | None:
        path = self.path_for(project_name)

        if not path.is_file():
            return None

        return OrchestrationState.model_validate_json(
            path.read_text(
                encoding="utf-8-sig"
            )
        )

    def save(
        self,
        state: OrchestrationState,
    ) -> Path:
        path = self.path_for(
            state.project_name
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        updated = state.model_copy(
            update={
                "updated_at": (
                    datetime.now(timezone.utc)
                    .isoformat()
                )
            }
        )

        path.write_text(
            updated.model_dump_json(indent=2),
            encoding="utf-8",
        )

        return path
