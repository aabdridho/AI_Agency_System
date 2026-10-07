from __future__ import annotations
import re, subprocess
from pathlib import Path
from .models import DeploymentPlan, DeploymentResult

class DeploymentExecutionError(RuntimeError):
    pass

class DeploymentExecutor:
    URL_RE = re.compile(r"https://[^\s]+")
    def __init__(self, repo):
        self.repo = Path(repo)

    def execute(self, plan: DeploymentPlan, *, approved: bool):
        if plan.status != "ready":
            return DeploymentResult(status="blocked", output_tail="Deployment plan is not ready.")
        if plan.mode == "dry-run":
            return DeploymentResult(status="planned")
        if not approved:
            raise DeploymentExecutionError("Explicit deployment approval is required.")

        executed, outputs = [], []
        for step in plan.commands:
            rendered = " ".join(step.command)
            executed.append(rendered)
            proc = subprocess.run(step.command, cwd=self.repo, capture_output=True, text=True, encoding="utf-8", errors="replace")
            out = (proc.stdout or "") + "\n" + (proc.stderr or "")
            outputs.append(out)
            if proc.returncode != 0:
                return DeploymentResult(status="failed", executed_commands=executed, output_tail=out.strip()[-3000:])

        all_output = "\n".join(outputs)
        urls = self.URL_RE.findall(all_output)
        return DeploymentResult(
            status="deployed",
            executed_commands=executed,
            output_tail=all_output.strip()[-3000:],
            deployment_url=urls[-1] if urls else None,
        )
