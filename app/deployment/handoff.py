from __future__ import annotations

import re
from pathlib import Path

from .models import (
    DeploymentPlan,
    DeploymentResult,
    HandoffReport,
)


class HandoffBuilder:
    def __init__(self, repo):
        self.repo = Path(repo)

    def _env_vars(self):
        p = self.repo / ".env.example"

        if not p.exists():
            return []

        out = []

        for line in p.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines():
            m = re.match(
                r"\s*([A-Z][A-Z0-9_]*)\s*=",
                line,
            )

            if m:
                out.append(m.group(1))

        return sorted(set(out))

    def _project_files(self):
        names = [
            "README.md",
            "docs/requirement.md",
            "docs/architecture.md",
            "docs/deployment.md",
            ".env.example",
            "package.json",
        ]

        return [
            n
            for n in names
            if (self.repo / n).exists()
        ]

    def build(
        self,
        *,
        plan: DeploymentPlan,
        result: DeploymentResult | None,
        delivery_report: dict,
        output_dir,
    ):
        out = Path(output_dir)
        out.mkdir(
            parents=True,
            exist_ok=True,
        )

        remaining = (
            [delivery_report["client_input_request"]]
            if delivery_report.get("client_input_request")
            else []
        )

        if result is not None:
            deployment_status = result.status
        elif plan.mode == "dry-run":
            deployment_status = "planned"
        else:
            deployment_status = plan.status

        report = HandoffReport(
            project_name=plan.project_name,
            project_root=plan.project_root,
            provider=plan.provider,
            source_branch=plan.source_branch,
            commit_sha=plan.commit_sha,
            delivery_status=delivery_report.get(
                "overall_status"
            ),
            deployment_status=deployment_status,
            deployment_url=(
                result.deployment_url
                if result
                else None
            ),
            environment_variables=self._env_vars(),
            validation_commands=(
                delivery_report.get(
                    "production_commands"
                )
                or []
            ),
            remaining_client_inputs=remaining,
            files=self._project_files(),
        )

        (
            out / "handoff_report.json"
        ).write_text(
            report.model_dump_json(indent=2),
            encoding="utf-8",
        )

        lines = [
            f"# Project Handoff - {plan.project_name}",
            "",
            "## Release",
            "",
            f"- Provider: `{plan.provider}`",
            f"- Source branch: `{plan.source_branch or 'unknown'}`",
            f"- Commit: `{plan.commit_sha or 'unknown'}`",
            f"- Delivery status: `{report.delivery_status or 'unknown'}`",
            f"- Deployment status: `{report.deployment_status or 'unknown'}`",
        ]

        if report.deployment_url:
            lines.append(
                f"- Deployment URL: {report.deployment_url}"
            )

        lines += [
            "",
            "## Runtime Environment",
            "",
        ]

        lines += (
            [
                f"- `{name}`"
                for name in report.environment_variables
            ]
            or [
                "- No environment variables documented."
            ]
        )

        lines += [
            "",
            "## Validation",
            "",
        ]

        lines += (
            [
                f"- `{cmd}`"
                for cmd in report.validation_commands
            ]
            or [
                "- No validation commands recorded."
            ]
        )

        lines += [
            "",
            "## Key Files",
            "",
        ]

        lines += [
            f"- `{name}`"
            for name in report.files
        ]

        if remaining:
            lines += [
                "",
                "## Remaining Client Inputs",
                "",
            ]

            lines += [
                f"- `{item}`"
                for item in remaining
            ]

        lines += [
            "",
            "## Safety",
            "",
            "- V0.9 does not merge or push `main`/`master` automatically.",
            "- Remote deployment requires explicit approval in the deployment CLI.",
            "- Environment values are never copied into the handoff report; only variable names are listed.",
            "- Dry-run handoff reports use `planned` deployment status and do not represent a completed production deployment.",
        ]

        (
            out / "handoff_report.md"
        ).write_text(
            "\n".join(lines) + "\n",
            encoding="utf-8",
        )

        return report
