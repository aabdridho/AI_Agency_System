from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.dashboard import DashboardService, ProjectNotFound
from app.dashboard.models import ProjectDetail, ProjectSummary, TierConfig
from app.discovery.confirmation import ConfirmationGate
from app.discovery.engine import RequirementDiscoveryEngine
from app.models.schemas import DiscoveryResult
from app.workspace import OUTPUT_ROOT, SYSTEM_ROOT

app = FastAPI(title="AI Agency System API", version="0.10.0")
engine = RequirementDiscoveryEngine()
gate = ConfirmationGate()

WEB_DIST = SYSTEM_ROOT / "web" / "dist"


class DiscoveryRequest(BaseModel):
    prompt: str = Field(min_length=1)
    references: list[str] = []


class ConfirmationRequest(BaseModel):
    result: DiscoveryResult
    key: str
    value: str | bool | int | float | list[str]


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.10.0"}


@app.post("/discover", response_model=DiscoveryResult)
def discover(payload: DiscoveryRequest):
    return engine.analyze(payload.prompt, payload.references)


@app.post("/confirm", response_model=DiscoveryResult)
def confirm(payload: ConfirmationRequest):
    return gate.promote_confirmed(payload.result, payload.key, payload.value)


# ---------- dashboard (read-only, plus saving a routing plan) ----------
# Execution and deployment stay in execute_project.py / deploy_project.py:
# they run Claude Code, Codex, git and remote deploys, so they need a human
# at the terminal.

def get_dashboard() -> DashboardService:
    return DashboardService(runtime_root=SYSTEM_ROOT / "runtime_data", output_root=OUTPUT_ROOT)


@app.get("/api/projects", response_model=list[ProjectSummary])
def list_projects(svc: DashboardService = Depends(get_dashboard)):
    return svc.list_projects()


@app.get("/api/projects/{name}", response_model=ProjectDetail)
def project_detail(name: str, svc: DashboardService = Depends(get_dashboard)):
    try:
        return svc.detail(name)
    except ProjectNotFound:
        raise HTTPException(404, f"Project '{name}' tidak ditemukan")


@app.post("/api/projects/{name}/route", response_model=ProjectDetail)
def save_routing(name: str, svc: DashboardService = Depends(get_dashboard)):
    try:
        return svc.save_routing(name)
    except ProjectNotFound:
        raise HTTPException(404, f"Project '{name}' tidak ditemukan di AI_Output")
    except FileNotFoundError:
        raise HTTPException(409, "docs/task.md belum ada. Jalankan discovery + documentation dulu.")
    except ValueError as exc:
        raise HTTPException(409, str(exc))


@app.get("/api/config")
def get_config(svc: DashboardService = Depends(get_dashboard)):
    return svc.get_config()


@app.put("/api/config")
def put_config(cfg: TierConfig, svc: DashboardService = Depends(get_dashboard)):
    return svc.save_config(cfg)


# Built frontend (cd web && npm run build). Mounted last so API routes win.
if WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=Path(WEB_DIST), html=True), name="web")

