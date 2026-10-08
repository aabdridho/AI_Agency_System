from __future__ import annotations
from app.command_resolver import resolve_node_cli
import json, shutil, subprocess
from pathlib import Path
from .models import DeploymentCommand, DeploymentPlan

class DeploymentPlanner:
    def __init__(self, repo):
        self.repo = Path(repo)

    def _run(self, args):
        return subprocess.run(args, cwd=self.repo, capture_output=True, text=True, encoding="utf-8", errors="replace")

    def _branch(self):
        p = self._run(["git", "branch", "--show-current"])
        return p.stdout.strip() if p.returncode == 0 else None

    def _sha(self):
        p = self._run(["git", "rev-parse", "HEAD"])
        return p.stdout.strip() if p.returncode == 0 else None

    def _clean(self):
        p = self._run(["git", "status", "--porcelain"])
        return p.returncode == 0 and not p.stdout.strip()

    def _provider_from_docs(self):
        for name in ("deployment.md", "architecture.md", "requirement.md"):
            path = self.repo / "docs" / name
            if path.exists() and "vercel" in path.read_text(encoding="utf-8", errors="replace").lower():
                return "vercel"
        return "unknown"

    def _is_nextjs(self):
        p = self.repo / "package.json"
        if not p.exists():
            return False
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return False
        deps = {}
        deps.update(data.get("dependencies") or {})
        deps.update(data.get("devDependencies") or {})
        return "next" in deps

    def create_plan(self, *, project_name, mode="dry-run"):
        branch = self._branch()
        provider = self._provider_from_docs()
        blockers, notes, commands = [], [], []

        if not self._clean():
            blockers.append("Git working tree is not clean.")
        if not branch or not branch.startswith("ai/integration/"):
            blockers.append("Deployment source must be an ai/integration/* branch.")
        if provider == "unknown":
            blockers.append("Deployment provider is unresolved.")

        if provider == "vercel":
            if not self._is_nextjs():
                blockers.append("Vercel auto-plan currently supports the validated Next.js path only.")
            npx = resolve_node_cli("npx")
            if not npx:
                blockers.append("npx is unavailable; cannot invoke Vercel CLI.")
            else:
                commands.append(DeploymentCommand(
                    label="Vercel production deploy",
                    command=[npx, "--yes", "vercel", "--prod"],
                    destructive_or_remote=True,
                ))
                notes.append("Vercel authentication/project linking may still require local CLI interaction.")

        return DeploymentPlan(
            project_name=project_name,
            project_root=str(self.repo),
            provider=provider,
            mode=mode,
            status="blocked" if blockers else "ready",
            source_branch=branch,
            commit_sha=self._sha(),
            commands=commands,
            blockers=blockers,
            notes=notes,
        )
