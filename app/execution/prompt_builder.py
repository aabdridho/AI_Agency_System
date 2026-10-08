from pathlib import Path


class TaskPromptBuilder:
    FRONTEND_HINTS = (
        "frontend",
        "ui",
        "ux",
        "page",
        "component",
        "layout",
        "responsive",
        "css",
        "style",
        "hero",
        "section",
        "landing page",
        "website",
        "visual",
    )

    BACKEND_HINTS = (
        "backend",
        "api",
        "server",
        "database",
        "db",
        "auth",
        "authentication",
        "endpoint",
        "route",
        "webhook",
        "submission",
        "submit",
        "contact form",
    )

    def _relevant_docs(self, task_text: str) -> list[str]:
        text = task_text.lower()

        frontend = any(hint in text for hint in self.FRONTEND_HINTS)
        backend = any(hint in text for hint in self.BACKEND_HINTS)

        docs = [
            "requirement.md",
            "architecture.md",
        ]

        if frontend:
            docs.append("frontend.md")

        if backend:
            docs.append("backend.md")

        # Ambiguous implementation work gets both domain documents.
        if not frontend and not backend:
            docs.extend([
                "frontend.md",
                "backend.md",
            ])

        return docs

    def build(self, project_root: str | Path, task_text: str) -> str:
        root = Path(project_root)
        docs = root / "docs"

        pieces = [
            "You are working inside a client project repository.",
            "Implement ONLY the assigned task and do not expand scope.",
            "",
            f"ASSIGNED TASK:\n{task_text}",
            "",
        ]

        for name in self._relevant_docs(task_text):
            path = docs / name

            if path.exists():
                pieces += [
                    f"--- {name} ---",
                    path.read_text(
                        encoding="utf-8",
                        errors="replace",
                    ),
                    "",
                ]

        pieces += [
            "EXECUTION CONTRACT:",
            "- Work directly in the current repository.",
            "- You MUST create or modify the files needed to complete the assigned task.",
            "- Do not merely explain, propose, or print code for the user to copy.",
            "- Leave the completed file changes in the working tree; the orchestrator handles Git commits.",
            "",
            "RULES:",
            "- Do not modify unrelated scope.",
            "- Do not commit secrets.",
            "- Keep changes minimal and production-oriented.",
            "- Respect project documentation as source of truth.",
            "- Do not modify operational AI logs.",
        ]

        return "\n".join(pieces)
