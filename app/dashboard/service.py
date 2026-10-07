"""Read-only view of every project for the web dashboard.

Collects the artifacts that the CLI scripts already write (docs/*.md inside the
client project, JSON reports under runtime_data/) and turns them into one
payload per project. Nothing here runs Claude Code, Codex, git, or deployment.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.dashboard.models import (
    STAGE_KEYS,
    ProjectDetail,
    ProjectSummary,
    StageState,
    TierConfig,
)
from app.routing.engine import RoutingEngine
from app.routing.storage import RoutingStorage

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")

RUNTIME_DIRS = ("routing", "execution", "delivery", "deployment", "handoff")


class ProjectNotFound(LookupError):
    pass


def valid_name(name: str) -> bool:
    return bool(NAME_RE.match(name)) and ".." not in name


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


class DashboardService:
    def __init__(self, runtime_root: Path, output_root: Path):
        self.runtime_root = Path(runtime_root)
        self.output_root = Path(output_root)

    # ---------- discovery of project names ----------
    def project_names(self) -> list[str]:
        names: set[str] = set()
        if self.output_root.is_dir():
            names.update(p.name for p in self.output_root.iterdir() if p.is_dir())
        for sub in RUNTIME_DIRS:
            d = self.runtime_root / sub
            if d.is_dir():
                names.update(p.name for p in d.iterdir() if p.is_dir())
        return sorted(n for n in names if valid_name(n))

    def _root(self, name: str) -> Path | None:
        root = self.output_root / name
        return root if root.is_dir() else None

    # ---------- artifacts ----------
    def _artifacts(self, name: str) -> dict[str, Any]:
        rt = self.runtime_root
        return {
            "routing": _read_json(rt / "routing" / name / "routing_plan.json"),
            "execution": _read_json(rt / "execution" / name / "execution_report.json"),
            "delivery": _read_json(rt / "delivery" / name / "delivery_report.json"),
            "deployment_plan": _read_json(rt / "deployment" / name / "deployment_plan.json"),
            "deployment_result": _read_json(rt / "deployment" / name / "deployment_result.json"),
            "handoff": _read_json(rt / "handoff" / name / "handoff_report.json"),
        }

    def _stages(self, root: Path | None, a: dict[str, Any], has_preview: bool) -> list[StageState]:
        docs = root / "docs" if root else None
        has = lambda f: bool(docs and (docs / f).is_file())  # noqa: E731

        def st(key: str, status: str, detail: str) -> StageState:
            return StageState(key=key, status=status, detail=detail)

        out: list[StageState] = []

        # discovery
        if has("discovery.md") or has("requirement.md"):
            out.append(st("discovery", "done", "requirement disetujui"))
        else:
            out.append(st("discovery", "todo", "belum ada brief"))

        # documentation
        if has("task.md"):
            out.append(st("documentation", "done", "task.md siap"))
        else:
            out.append(st("documentation", "todo", "task.md belum ada"))

        # routing
        plan = a["routing"]
        if plan:
            n = len(plan.get("decisions", []))
            out.append(st("routing", "done", f"{n} task dirouting"))
        elif has_preview:
            out.append(st("routing", "wait", "preview · belum disimpan"))
        else:
            out.append(st("routing", "todo", "belum dirouting"))

        # execution
        ex = a["execution"]
        if ex:
            recs = ex.get("records", [])
            failed = sum(1 for r in recs if r.get("status") == "failed")
            if ex.get("dry_run"):
                out.append(st("execution", "wait", f"dry-run · {len(recs)} task"))
            elif failed:
                out.append(st("execution", "fail", f"{failed} task gagal"))
            else:
                out.append(st("execution", "done", f"{len(recs)} task selesai"))
        else:
            out.append(st("execution", "todo", "belum dijalankan"))

        # delivery
        dl = a["delivery"]
        if dl:
            status = dl.get("overall_status")
            blockers = sum(1 for c in dl.get("checks", []) if c.get("status") == "blocker")
            if status == "ready":
                out.append(st("delivery", "done", "READY"))
            elif status == "warning":
                out.append(st("delivery", "wait", "ada warning"))
            else:
                out.append(st("delivery", "fail", f"{blockers} blocker"))
        else:
            out.append(st("delivery", "todo", "belum dicek"))

        # deployment
        res, dp = a["deployment_result"], a["deployment_plan"]
        if res and res.get("status") == "deployed":
            out.append(st("deployment", "done", res.get("deployment_url") or "deployed"))
        elif res and res.get("status") == "failed":
            out.append(st("deployment", "fail", "deploy gagal"))
        elif dp and dp.get("status") == "blocked":
            out.append(st("deployment", "fail", "diblokir guard"))
        elif dp:
            out.append(st("deployment", "wait", "tunggu approval"))
        else:
            out.append(st("deployment", "todo", "belum direncanakan"))

        return out

    def _preview_plan(self, root: Path | None) -> dict[str, Any] | None:
        if not root or not (root / "docs" / "task.md").is_file():
            return None
        try:
            return RoutingEngine().build_plan(root).model_dump()
        except (FileNotFoundError, ValueError):
            return None

    # ---------- public API ----------
    def summary(self, name: str) -> ProjectSummary:
        root = self._root(name)
        a = self._artifacts(name)
        has_preview = bool(not a["routing"] and root and (root / "docs" / "task.md").is_file())
        stages = self._stages(root, a, has_preview)
        return ProjectSummary(name=name, has_workspace=root is not None, stages=stages)

    def list_projects(self) -> list[ProjectSummary]:
        return [self.summary(n) for n in self.project_names()]

    def detail(self, name: str) -> ProjectDetail:
        if not valid_name(name) or name not in self.project_names():
            raise ProjectNotFound(name)
        root = self._root(name)
        a = self._artifacts(name)
        routing_source = "saved" if a["routing"] else None
        if not a["routing"]:
            preview = self._preview_plan(root)
            if preview:
                a["routing"] = preview
                routing_source = "preview"
        stages = self._stages(root, {**a, "routing": a["routing"] if routing_source == "saved" else None},
                              routing_source == "preview")
        return ProjectDetail(
            name=name,
            has_workspace=root is not None,
            stages=stages,
            routing_source=routing_source,
            **a,
        )

    def save_routing(self, name: str) -> ProjectDetail:
        if not valid_name(name):
            raise ProjectNotFound(name)
        root = self._root(name)
        if not root:
            raise ProjectNotFound(name)
        plan = RoutingEngine().build_plan(root)  # raises FileNotFoundError / ValueError
        RoutingStorage().save(plan, self.runtime_root)
        return self.detail(name)

    # ---------- tier config (stored only; execution adapters do not read it yet) ----------
    def _config_path(self) -> Path:
        return self.runtime_root / "config" / "tiers.json"

    def get_config(self) -> dict[str, Any]:
        data = _read_json(self._config_path())
        if data:
            try:
                return {"source": "saved", **TierConfig.model_validate(data).model_dump()}
            except ValueError:
                pass
        return {"source": "default", "tiers": None}

    def save_config(self, cfg: TierConfig) -> dict[str, Any]:
        path = self._config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cfg.model_dump(), indent=2), encoding="utf-8")
        return {"source": "saved", **cfg.model_dump()}


__all__ = ["DashboardService", "ProjectNotFound", "STAGE_KEYS", "valid_name"]
