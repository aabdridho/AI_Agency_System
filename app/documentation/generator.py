from pathlib import Path
from app.models.schemas import DiscoveryResult


class ProjectDocumentationGenerator:
    """
    V0.4 documentation generator.

    Generates project-facing documentation only.
    Operational AI/routing logs are intentionally excluded from project repos.
    """

    def _confirmed(self, result: DiscoveryResult) -> dict:
        return {item.key: item.value for item in result.confirmed}

    def _internal(self, result: DiscoveryResult) -> dict:
        return {
            item.key: item.value
            for item in result.internal_decisions
            if item.key != "discovery_engine_version"
        }

    def _fmt(self, value):
        if isinstance(value, list):
            return ", ".join(str(x) for x in value)
        return str(value)

    def _requires_backend(self, result: DiscoveryResult) -> bool:
        data = self._confirmed(result)
        return data.get("contact_behavior") == "contact_form"

    def _requires_frontend(self, result: DiscoveryResult) -> bool:
        return result.project_type in {"portfolio", "website", "landing_page", "web_app"}

    def render_requirement(self, result: DiscoveryResult) -> str:
        lines = [
            "# Project Requirements",
            "",
            "## Status",
            "CLIENT_APPROVED" if result.client_approved else "DRAFT",
            "",
            "## Project Type",
            result.project_type,
            "",
            "## Confirmed Requirements",
        ]

        for item in result.confirmed:
            lines.append(f"- **{item.key}**: {self._fmt(item.value)}")

        internal = self._internal(result)
        if internal:
            lines += ["", "## Internal Technical Decisions"]
            for key, value in internal.items():
                lines.append(f"- **{key}**: {self._fmt(value)}")

        lines += [
            "",
            "## Implementation Gate",
            f"- Client approved: {result.client_approved}",
            f"- Ready for development: {result.ready_for_development}",
            "- Implementation may use only confirmed requirements plus documented internal decisions.",
            "- Any client-facing scope change requires requirement confirmation before implementation.",
            "",
        ]
        return "\n".join(lines)

    def render_task(self, result: DiscoveryResult) -> str:
        data = self._confirmed(result)
        sections = data.get("required_sections", [])
        if not isinstance(sections, list):
            sections = [str(sections)]

        lines = [
            "# Project Tasks",
            "",
            "## Source of Truth",
            "- Derived from `docs/requirement.md`.",
            "- Do not add client-facing scope that is not confirmed.",
            "",
            "## Setup",
            "- [ ] Initialize project structure and development environment",
            "- [ ] Apply repository quality rules (formatter, linting, tests where applicable)",
        ]

        if self._requires_frontend(result):
            lines += [
                "",
                "## Frontend",
                "- [ ] Establish page layout and design system from confirmed visual direction",
            ]
            for section in sections:
                lines.append(f"- [ ] Implement `{section}` section")

            if data.get("theme"):
                lines.append(f"- [ ] Apply confirmed `{data['theme']}` theme")

            if data.get("reference_urls"):
                lines.append("- [ ] Use approved reference aspects as inspiration without copying unconfirmed details")

        if data.get("contact_behavior") == "display_only":
            lines += [
                "",
                "## Contact",
                "- [ ] Implement display-only contact information",
            ]

        if data.get("contact_behavior") == "contact_form":
            fields = data.get("contact_fields", [])
            destination = data.get("contact_destination", "confirmed destination")
            lines += [
                "",
                "## Contact Form",
                f"- [ ] Implement form fields: {self._fmt(fields)}",
                "- [ ] Add client-side validation",
                f"- [ ] Submit form data to `{destination}`",
                "- [ ] Add success and failure states",
                "- [ ] Validate submission flow end-to-end",
            ]

        lines += [
            "",
            "## QA",
            "- [ ] Verify implementation against every confirmed requirement",
            "- [ ] Run deterministic validation/lint/tests",
            "- [ ] Check responsive behavior where applicable",
            "- [ ] Confirm no unapproved scope was introduced",
            "",
        ]
        return "\n".join(lines)

    def render_architecture(self, result: DiscoveryResult) -> str:
        data = self._confirmed(result)
        internal = self._internal(result)

        components = []
        if self._requires_frontend(result):
            components.append("Frontend / presentation layer")
        if self._requires_backend(result):
            components.append("Submission handling layer for the confirmed contact form")
        if data.get("contact_destination") == "email":
            components.append("Email delivery integration")
        elif data.get("contact_destination"):
            components.append(f"Contact integration: {data['contact_destination']}")

        lines = [
            "# Architecture",
            "",
            "## Architecture Status",
            "This document is derived from approved requirements. Technology choices that the client did not constrain remain internal decisions.",
            "",
            "## Required Components",
        ]
        for component in components or ["Project implementation layer"]:
            lines.append(f"- {component}")

        lines += [
            "",
            "## Boundaries",
            "- Client-confirmed behavior is authoritative.",
            "- Framework/library choices are internal unless explicitly constrained by the client.",
            "- Operational AI logs, token usage, routing decisions, and model traces must not be stored in the project repository.",
            "- Secrets and credentials must not be committed to source control.",
        ]

        if internal:
            lines += ["", "## Current Internal Decisions"]
            for key, value in internal.items():
                lines.append(f"- **{key}**: {self._fmt(value)}")

        lines += ["", "## Pending Internal Decisions"]
        if internal.get("deployment_target") == "to_be_decided_internally":
            lines.append("- Deployment target")
        lines.append("- Concrete framework/tooling selection where not client-constrained")
        lines.append("")
        return "\n".join(lines)

    def render_frontend(self, result: DiscoveryResult) -> str:
        data = self._confirmed(result)
        sections = data.get("required_sections", [])
        refs = data.get("reference_urls", [])
        prefs = data.get("reference_preferences", [])

        lines = [
            "# Frontend Specification",
            "",
            "## Visual Requirements",
            f"- Visual direction: {self._fmt(data.get('visual_direction', 'not specified'))}",
            f"- Theme: {self._fmt(data.get('theme', 'not specified'))}",
            f"- Target audience: {self._fmt(data.get('target_audience', 'not specified'))}",
            "",
            "## Required Sections",
        ]
        for section in sections if isinstance(sections, list) else [sections]:
            lines.append(f"- {section}")

        if refs:
            lines += [
                "",
                "## References",
                f"- URLs: {self._fmt(refs)}",
                f"- Approved aspects to use as inspiration: {self._fmt(prefs) if prefs else 'not specified'}",
                "- References are inspiration only; do not infer unconfirmed functionality from them.",
            ]

        lines += [
            "",
            "## Interaction Notes",
            f"- Contact behavior: {self._fmt(data.get('contact_behavior', 'not specified'))}",
            "- Responsive and accessibility details should follow internal engineering standards unless the client adds constraints.",
            "",
        ]
        return "\n".join(lines)

    def render_backend(self, result: DiscoveryResult) -> str:
        data = self._confirmed(result)
        return "\n".join([
            "# Backend Specification",
            "",
            "## Scope",
            "Backend/server-side handling is required because the approved requirements include a data-submitting contact form.",
            "",
            "## Contact Submission",
            f"- Destination: {self._fmt(data.get('contact_destination'))}",
            f"- Required fields: {self._fmt(data.get('contact_fields', []))}",
            "- Validate/sanitize submitted data.",
            "- Return clear success/failure outcomes to the frontend.",
            "- Keep credentials/secrets outside source control.",
            "",
            "## Out of Scope",
            "- No additional API, authentication, database, CRM, or admin functionality unless separately confirmed.",
            "",
        ])

    def render_deployment(self, result: DiscoveryResult) -> str:
        internal = self._internal(result)
        target = internal.get("deployment_target", "to_be_decided_internally")
        return "\n".join([
            "# Deployment",
            "",
            "## Current Decision",
            f"- Deployment target: {target}",
            "",
            "## Rules",
            "- Deployment platform is an internal technical choice unless constrained by the client.",
            "- Production deployment must occur only after requirement and QA checks pass.",
            "- Secrets must use environment variables or a secure secret store.",
            "- Do not deploy operational AI logs with the client/project application.",
            "",
        ])

    def render_discovery(self, result: DiscoveryResult) -> str:
        lines = [
            "# Requirement Discovery Record",
            "",
            "## Purpose",
            "Records how the approved project requirements were classified. This is project-facing audit context, not an operational AI log.",
            "",
            "## Confirmed",
        ]
        for item in result.confirmed:
            lines.append(
                f"- **{item.key}** = {self._fmt(item.value)} "
                f"(source: `{item.source}`)"
            )

        if result.inferred:
            lines += ["", "## Inferred (not implementation authority)"]
            for item in result.inferred:
                lines.append(f"- **{item.key}** = {self._fmt(item.value)}")

        if result.proposed:
            lines += ["", "## Proposed (not implementation authority)"]
            for item in result.proposed:
                lines.append(f"- **{item.key}** = {self._fmt(item.value)}")

        lines += [
            "",
            "## Approval",
            f"- Client approved final requirement: {result.client_approved}",
            f"- Ready for development: {result.ready_for_development}",
            "",
        ]
        return "\n".join(lines)

    def generate(self, result: DiscoveryResult, project_root: str | Path) -> list[Path]:
        if not result.client_approved or not result.ready_for_development:
            raise ValueError(
                "Project documentation cannot be finalized before client approval."
            )

        root = Path(project_root)
        docs = root / "docs"
        docs.mkdir(parents=True, exist_ok=True)

        files = {
            docs / "requirement.md": self.render_requirement(result),
            docs / "task.md": self.render_task(result),
            docs / "architecture.md": self.render_architecture(result),
            docs / "deployment.md": self.render_deployment(result),
            docs / "discovery.md": self.render_discovery(result),
        }

        if self._requires_frontend(result):
            files[docs / "frontend.md"] = self.render_frontend(result)

        if self._requires_backend(result):
            files[docs / "backend.md"] = self.render_backend(result)

        for path, content in files.items():
            path.write_text(content, encoding="utf-8")

        changelog = root / "CHANGELOG.md"
        changelog.write_text(
            "# Changelog\n\n"
            "## Initial approved baseline\n"
            "- Project documentation generated from client-approved requirements.\n"
            "- Future revisions must update affected documentation before implementation.\n",
            encoding="utf-8",
        )
        files[changelog] = changelog.read_text(encoding="utf-8")

        return list(files.keys())
