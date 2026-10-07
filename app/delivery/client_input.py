from __future__ import annotations

import re
from pathlib import Path

from .models import ClientInputItem, ReadinessCheck


class ClientInputPacketGenerator:
    """
    Build a deterministic client-input request packet from delivery blockers.
    This generator never modifies the project repo and never invents client data.
    """

    SECTION_FIELDS = {
        "hero": [
            "Full name / display name",
            "Professional headline or role",
            "Short introduction (1-3 sentences)",
            "Primary CTA label and destination",
        ],
        "about": [
            "Short professional biography",
            "Current role / study / professional status",
            "Primary professional focus",
            "Key differentiators or strengths to highlight",
        ],
        "contact": [
            "Public contact email",
            "LinkedIn URL (if intended for publication)",
            "GitHub URL (if intended for publication)",
            "Location (optional)",
        ],
        "experience": [
            "Role / position title",
            "Organization / company",
            "Start and end dates",
            "Approved responsibility / achievement bullets",
        ],
        "projects": [
            "Project name",
            "Short description",
            "Technology stack",
            "Project/repository/live URL if public",
            "Approved outcome / impact",
        ],
        "skills": [
            "Skills/technologies approved for publication",
            "Preferred grouping or proficiency wording, if any",
        ],
        "certifications": [
            "Certification name",
            "Issuer",
            "Issue date",
            "Credential URL/ID if public",
        ],
    }

    CONTENT_PATH_RE = re.compile(
        r"(?:src/content|public)/[^,\s]+",
        flags=re.I,
    )

    def __init__(self, repo: str | Path):
        self.repo = Path(repo)

    def _placeholder_files_from_checks(self, checks: list[ReadinessCheck]) -> list[str]:
        files = []
        for check in checks:
            if (
                check.status == "blocker"
                and check.blocker_class == "CLIENT_INPUT_REQUIRED"
                and check.check_id == "placeholder_content"
            ):
                files.extend(
                    m.rstrip(".,;:")
                    for m in self.CONTENT_PATH_RE.findall(check.detail)
                )
        return sorted(set(files))

    def _section_for_path(self, rel_path: str) -> str:
        return Path(rel_path).stem.lower()

    def build_items(self, checks: list[ReadinessCheck]) -> list[ClientInputItem]:
        items = []
        for rel_path in self._placeholder_files_from_checks(checks):
            section = self._section_for_path(rel_path)
            fields = self.SECTION_FIELDS.get(
                section,
                ["Approved final content for this section"],
            )
            items.append(
                ClientInputItem(
                    section=section,
                    source_file=rel_path,
                    fields=fields,
                    note="Provide only information approved for public display.",
                )
            )

        # Requirement approval is also client-owned, though not content-file based.
        if any(
            c.status == "blocker"
            and c.blocker_class == "CLIENT_INPUT_REQUIRED"
            and c.check_id == "requirement_gate"
            for c in checks
        ):
            items.append(
                ClientInputItem(
                    section="requirements_approval",
                    source_file="docs/requirement.md",
                    fields=["Explicit approval of the final confirmed requirements"],
                    note="Implementation/delivery must not proceed without approval.",
                )
            )

        # Stable order keeps reports deterministic.
        return sorted(items, key=lambda x: (x.section, x.source_file or ""))

    def render_markdown(
        self,
        *,
        project_name: str,
        checks: list[ReadinessCheck],
    ) -> str | None:
        items = self.build_items(checks)
        if not items:
            return None

        lines = [
            f"# Client Input Request - {project_name}",
            "",
            "Delivery is technically validated, but the following client-owned information is still required.",
            "",
            "## Rules",
            "",
            "- Do not invent or infer personal/client facts.",
            "- Provide only information approved for public display.",
            "- Optional fields may be omitted.",
            "- After these inputs are supplied and applied, rerun `python prepare_delivery.py`.",
            "",
            "## Requested Inputs",
            "",
        ]

        for index, item in enumerate(items, start=1):
            title = item.section.replace("_", " ").title()
            lines.append(f"### {index}. {title}")
            if item.source_file:
                lines.append(f"- Source: `{item.source_file}`")
            lines.append("- Please provide:")
            for field in item.fields:
                lines.append(f"  - {field}")
            if item.note:
                lines.append(f"- Note: {item.note}")
            lines.append("")

        return "\n".join(lines).rstrip() + "\n"
