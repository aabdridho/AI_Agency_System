from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .models import (
    AgentHeartbeat,
    AgentRecord,
    AgentStateUpdate,
)
from .registry import AgentNotFound, registry


router = APIRouter(
    prefix="/api/agents",
    tags=["agents"],
)


def _not_found(exc: AgentNotFound) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail="Agent tidak ditemukan.",
    )


@router.get("", response_model=list[AgentRecord])
def list_agents() -> list[AgentRecord]:
    return registry.list_agents()


@router.get("/{agent_id}", response_model=AgentRecord)
def get_agent(agent_id: str) -> AgentRecord:
    try:
        return registry.get_agent(agent_id)
    except AgentNotFound as exc:
        raise _not_found(exc) from exc


@router.post("/{agent_id}/state", response_model=AgentRecord)
def update_agent_state(
    agent_id: str,
    payload: AgentStateUpdate,
) -> AgentRecord:
    try:
        return registry.update_state(agent_id, payload)
    except AgentNotFound as exc:
        raise _not_found(exc) from exc


@router.post("/{agent_id}/heartbeat", response_model=AgentRecord)
def heartbeat(
    agent_id: str,
    payload: AgentHeartbeat,
) -> AgentRecord:
    try:
        return registry.heartbeat(agent_id, payload)
    except AgentNotFound as exc:
        raise _not_found(exc) from exc
