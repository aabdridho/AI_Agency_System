from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    ERROR = "error"
    OFFLINE = "offline"


class AgentRecord(BaseModel):
    id: str
    name: str
    role: str
    provider: str
    model_name: str
    status: AgentStatus = AgentStatus.IDLE

    current_task: str | None = None
    project: str | None = None
    run_id: str | None = None
    session_id: str | None = None

    last_activity: str | None = None
    heartbeat_at: str | None = None


class AgentStateUpdate(BaseModel):
    status: AgentStatus
    current_task: str | None = None
    project: str | None = None
    run_id: str | None = None
    session_id: str | None = None


class AgentHeartbeat(BaseModel):
    current_task: str | None = None
    project: str | None = None
    run_id: str | None = None
    session_id: str | None = None
