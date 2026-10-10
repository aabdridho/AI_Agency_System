from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.workspace import SYSTEM_ROOT

from .models import (
    AgentHeartbeat,
    AgentRecord,
    AgentStateUpdate,
    AgentStatus,
)


class AgentNotFound(KeyError):
    pass


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AgentRegistry:
    RUNNING_STALE_AFTER_SECONDS = 20.0

    def __init__(
        self,
        state_path: str | Path | None = None,
    ) -> None:
        self.state_path = (
            Path(state_path)
            if state_path is not None
            else None
        )

        self._agents = self._bootstrap_agents()
        self._refresh_from_disk()

    def _bootstrap_agents(self) -> dict[str, AgentRecord]:
        return {
            "codex": AgentRecord(
                id="codex",
                name="Codex",
                role="backend_engineering",
                provider="openai",
                model_name="codex",
                status=AgentStatus.IDLE,
            ),
            "claude-code": AgentRecord(
                id="claude-code",
                name="Claude Code",
                role="frontend_ui",
                provider="anthropic",
                model_name="claude-code",
                status=AgentStatus.IDLE,
            ),
            "deterministic-qa": AgentRecord(
                id="deterministic-qa",
                name="Deterministic QA",
                role="quality_assurance",
                provider="internal",
                model_name="deterministic",
                status=AgentStatus.IDLE,
            ),
            "deployment-guard": AgentRecord(
                id="deployment-guard",
                name="Deployment Guard",
                role="deployment_safety",
                provider="internal",
                model_name="deterministic",
                status=AgentStatus.IDLE,
            ),
        }

    def _refresh_from_disk(self) -> None:
        if self.state_path is None or not self.state_path.exists():
            return

        try:
            payload = json.loads(
                self.state_path.read_text(encoding="utf-8")
            )

            loaded = {}

            for item in payload:
                agent = AgentRecord.model_validate(item)
                loaded[agent.id] = agent

            bootstrap = self._bootstrap_agents()
            bootstrap.update(loaded)

            self._agents = bootstrap

        except Exception:
            return

    def _persist(self) -> None:
        if self.state_path is None:
            return

        self.state_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        payload = [
            agent.model_dump(mode="json")
            for agent in self._agents.values()
        ]

        temporary = self.state_path.with_suffix(
            self.state_path.suffix + ".tmp"
        )

        temporary.write_text(
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        temporary.replace(self.state_path)

    def _refresh_stale_running_agents(self) -> None:
        now = datetime.now(timezone.utc)
        changed = False

        for agent in self._agents.values():
            if agent.status != AgentStatus.RUNNING:
                continue

            if not agent.heartbeat_at:
                continue

            try:
                heartbeat = datetime.fromisoformat(
                    agent.heartbeat_at
                )
            except ValueError:
                continue

            if heartbeat.tzinfo is None:
                heartbeat = heartbeat.replace(
                    tzinfo=timezone.utc
                )

            age = (
                now - heartbeat.astimezone(timezone.utc)
            ).total_seconds()

            if age <= self.RUNNING_STALE_AFTER_SECONDS:
                continue

            agent.status = AgentStatus.OFFLINE
            changed = True

        if changed:
            self._persist()

    def list_agents(self) -> list[AgentRecord]:
        self._refresh_from_disk()
        self._refresh_stale_running_agents()
        return list(self._agents.values())

    def get_agent(self, agent_id: str) -> AgentRecord:
        self._refresh_from_disk()
        self._refresh_stale_running_agents()

        agent = self._agents.get(agent_id)

        if agent is None:
            raise AgentNotFound(agent_id)

        return agent

    def update_state(
        self,
        agent_id: str,
        payload: AgentStateUpdate,
    ) -> AgentRecord:
        self._refresh_from_disk()

        agent = self._agents.get(agent_id)

        if agent is None:
            raise AgentNotFound(agent_id)

        agent.status = payload.status
        agent.current_task = payload.current_task
        agent.project = payload.project
        agent.run_id = payload.run_id
        agent.session_id = payload.session_id
        agent.last_activity = utc_now_iso()

        self._persist()

        return agent

    def heartbeat(
        self,
        agent_id: str,
        payload: AgentHeartbeat,
    ) -> AgentRecord:
        self._refresh_from_disk()

        agent = self._agents.get(agent_id)

        if agent is None:
            raise AgentNotFound(agent_id)

        now = utc_now_iso()

        agent.heartbeat_at = now
        agent.last_activity = now

        if payload.current_task is not None:
            agent.current_task = payload.current_task

        if payload.project is not None:
            agent.project = payload.project

        if payload.run_id is not None:
            agent.run_id = payload.run_id

        if payload.session_id is not None:
            agent.session_id = payload.session_id

        if agent.status == AgentStatus.OFFLINE:
            agent.status = AgentStatus.IDLE
            agent.current_task = None
            agent.project = None
            agent.run_id = None
            agent.session_id = None

        self._persist()

        return agent


AGENT_STATE_PATH = (
    SYSTEM_ROOT
    / "runtime_data"
    / "agents"
    / "state.json"
)


registry = AgentRegistry(
    state_path=AGENT_STATE_PATH,
)
