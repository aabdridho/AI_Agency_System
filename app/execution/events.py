from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


EventStatus = Literal[
    "pending",
    "running",
    "success",
    "failed",
    "skipped",
    "info",
]


class ExecutionEvent(BaseModel):
    timestamp: datetime
    project_name: str
    task_id: str | None = None

    event_type: str
    phase: str

    status: EventStatus = "info"

    owner: str | None = None
    model: str | None = None
    effort: str | None = None

    attempt: int = 1
    detail: str | None = None

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )


class ExecutionEventLedger:
    """
    Append-only runtime execution trace.

    This ledger describes lifecycle events only.
    Token/cost telemetry remains authoritative in UsageLedger.
    """

    def __init__(
        self,
        root: str | Path,
    ):
        self.root = Path(root)

    def _path(
        self,
        project_name: str,
    ) -> Path:
        return (
            self.root
            / project_name
            / "events.jsonl"
        )

    def append(
        self,
        *,
        project_name: str,
        event_type: str,
        phase: str,
        status: EventStatus = "info",
        task_id: str | None = None,
        owner: str | None = None,
        model: str | None = None,
        effort: str | None = None,
        attempt: int = 1,
        detail: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        path = self._path(project_name)
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        event = ExecutionEvent(
            timestamp=datetime.now(timezone.utc),
            project_name=project_name,
            task_id=task_id,
            event_type=event_type,
            phase=phase,
            status=status,
            owner=owner,
            model=model,
            effort=effort,
            attempt=attempt,
            detail=detail,
            metadata=metadata or {},
        )

        with path.open(
            "a",
            encoding="utf-8",
        ) as fh:
            fh.write(event.model_dump_json())
            fh.write("\n")

        return path

    def read(
        self,
        project_name: str,
    ) -> list[ExecutionEvent]:
        path = self._path(project_name)

        if not path.is_file():
            return []

        events: list[ExecutionEvent] = []

        for raw in path.read_text(
            encoding="utf-8"
        ).splitlines():
            raw = raw.strip()

            if not raw:
                continue

            try:
                events.append(
                    ExecutionEvent.model_validate(
                        json.loads(raw)
                    )
                )
            except (
                json.JSONDecodeError,
                ValueError,
            ):
                continue

        return events
