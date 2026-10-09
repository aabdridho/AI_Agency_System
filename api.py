from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.dashboard import DashboardService, ProjectNotFound
from app.dashboard.service import valid_name
from app.orchestration.orchestrator import ProjectOrchestrator
from app.dashboard.models import ProjectDetail, ProjectSummary, TierConfig
from app.discovery.confirmation import ConfirmationGate
from app.discovery.engine import RequirementDiscoveryEngine
from app.models.schemas import DiscoveryResult
from app.workspace import OUTPUT_ROOT, SYSTEM_ROOT
from app.agents.router import router as agents_router
from app.execution.billing import BillingPolicy

app = FastAPI(title="AI Agency System API", version="0.16.0")
app.include_router(agents_router)
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


class ProjectIntakeRequest(BaseModel):
    project_name: str = Field(min_length=1, max_length=100)
    brief: str = Field(min_length=1)
    references: list[str] = []


class ProjectIntakeResponse(BaseModel):
    project_name: str
    discovery: DiscoveryResult


class ProjectConfirmationRequest(BaseModel):
    project_name: str = Field(min_length=1, max_length=100)
    result: DiscoveryResult
    answers: dict[
        str,
        str | bool | int | float | list[str],
    ]


class ProjectApprovalRequest(BaseModel):
    project_name: str = Field(min_length=1, max_length=100)
    result: DiscoveryResult


class ProjectApprovalResponse(BaseModel):
    project_name: str
    discovery: DiscoveryResult
    generated_docs: list[str]


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.16.0"}


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


def get_orchestrator() -> ProjectOrchestrator:
    return ProjectOrchestrator(
        runtime_root=SYSTEM_ROOT / "runtime_data",
        output_root=OUTPUT_ROOT,
    )


@app.post(
    "/api/projects/intake",
    response_model=ProjectIntakeResponse,
)
def project_intake(
    payload: ProjectIntakeRequest,
    orchestrator: ProjectOrchestrator = Depends(get_orchestrator),
):
    project_name = payload.project_name.strip()

    if not valid_name(project_name):
        raise HTTPException(
            422,
            (
                "Nama project tidak valid. Gunakan huruf, angka, "
                "titik, underscore, atau dash; jangan gunakan '..'."
            ),
        )

    try:
        result = orchestrator.analyze_brief(
            payload.brief,
            payload.references,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    return ProjectIntakeResponse(
        project_name=project_name,
        discovery=result,
    )


@app.post(
    "/api/projects/intake/confirm",
    response_model=ProjectIntakeResponse,
)
def confirm_project_intake(
    payload: ProjectConfirmationRequest,
):
    project_name = payload.project_name.strip()

    if not valid_name(project_name):
        raise HTTPException(
            422,
            "Nama project tidak valid.",
        )

    result = payload.result

    for key, value in payload.answers.items():
        result = gate.promote_confirmed(
            result,
            key,
            value,
        )

    return ProjectIntakeResponse(
        project_name=project_name,
        discovery=result,
    )


@app.post(
    "/api/projects/intake/approve",
    response_model=ProjectApprovalResponse,
)
def approve_project_intake(
    payload: ProjectApprovalRequest,
    orchestrator: ProjectOrchestrator = Depends(get_orchestrator),
):
    project_name = payload.project_name.strip()

    if not valid_name(project_name):
        raise HTTPException(
            422,
            "Nama project tidak valid.",
        )

    try:
        approved = orchestrator.approve_discovery(
            payload.result,
        )

        generated = orchestrator.generate_documentation(
            project_name,
            approved,
        )

        # Documentation selesai. Lanjutkan semua safe automatic
        # stage sampai membutuhkan approval real execution.
        orchestrator.run_until_blocked(
            project_name,
            approve_real_execution=False,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(409, str(exc))
    except FileExistsError as exc:
        raise HTTPException(409, str(exc))

    return ProjectApprovalResponse(
        project_name=project_name,
        discovery=approved,
        generated_docs=[
            str(path.name)
            for path in generated
        ],
    )


@app.post("/api/projects/{name}/execute")
def execute_project_from_control_room(
    name: str,
    orchestrator: ProjectOrchestrator = Depends(get_orchestrator),
):
    if not valid_name(name):
        raise HTTPException(
            422,
            "Nama project tidak valid.",
        )

    try:
        return orchestrator.run_until_blocked(
            name,
            approve_real_execution=True,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            404,
            str(exc),
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(
            409,
            str(exc),
        )


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


@app.get("/api/projects/{name}/economics")
def project_economics(
    name: str,
    svc: DashboardService = Depends(get_dashboard),
):
    try:
        return svc.economics(name)
    except ProjectNotFound:
        raise HTTPException(
            404,
            f"Project '{name}' tidak ditemukan",
        )


@app.get("/api/billing/config")
def get_billing_config(
    svc: DashboardService = Depends(get_dashboard),
):
    return svc.get_billing_config()


@app.put("/api/billing/config")
def put_billing_config(
    policy: BillingPolicy,
    svc: DashboardService = Depends(get_dashboard),
):
    try:
        return svc.save_billing_config(policy)
    except ValueError as exc:
        raise HTTPException(422, str(exc))


# Built frontend (cd web && npm run build). Mounted last so API routes win.
if WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=Path(WEB_DIST), html=True), name="web")

