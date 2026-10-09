from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

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

    # Execution identity. Optional for backward compatibility
    # with V0.16 event rows created before run hardening.
    run_id: str | None = None
    event_id: str | None = None
    sequence: int | None = None

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
        self._sequence_by_run: dict[
            tuple[str, str],
            int,
        ] = {}

    def _path(
        self,
        project_name: str,
    ) -> Path:
        return (
            self.root
            / project_name
            / "events.jsonl"
        )

    def _next_sequence(
        self,
        project_name: str,
        run_id: str,
    ) -> int:
        key = (project_name, run_id)

        if key not in self._sequence_by_run:
            highest = 0
            path = self._path(project_name)

            if path.is_file():
                for raw in path.read_text(
                    encoding="utf-8"
                ).splitlines():
                    raw = raw.strip()

                    if not raw:
                        continue

                    try:
                        payload = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    if payload.get("run_id") != run_id:
                        continue

                    sequence = payload.get("sequence")

                    if isinstance(sequence, int):
                        highest = max(
                            highest,
                            sequence,
                        )

            self._sequence_by_run[key] = highest

        self._sequence_by_run[key] += 1

        return self._sequence_by_run[key]


    def append(
        self,
        *,
        project_name: str,
        event_type: str,
        phase: str,
        status: EventStatus = "info",
        task_id: str | None = None,
        run_id: str | None = None,
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

        sequence = (
            self._next_sequence(
                project_name,
                run_id,
            )
            if run_id
            else None
        )

        event = ExecutionEvent(
            timestamp=datetime.now(timezone.utc),
            project_name=project_name,
            task_id=task_id,
            run_id=run_id,
            event_id=uuid4().hex,
            sequence=sequence,
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
