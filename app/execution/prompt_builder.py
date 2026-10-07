from pathlib import Path

class TaskPromptBuilder:
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

        for name in ["requirement.md", "task.md", "architecture.md", "frontend.md", "backend.md"]:
            path = docs / name
            if path.exists():
                pieces += [
                    f"--- {name} ---",
                    path.read_text(encoding="utf-8"),
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
