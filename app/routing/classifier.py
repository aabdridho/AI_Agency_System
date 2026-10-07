class TaskClassifier:
    """
    Deterministic classifier for V0.5.

    Important distinction:
    - implementation work is routed to a coding owner
    - verification/checking work is routed to deterministic QA
    """

    def classify(self, task: str) -> tuple[str, float]:
        t = task.lower().strip()

        # ---- Explicit QA / audit checks ----
        qa_phrases = [
            "run deterministic validation",
            "run deterministic",
            "lint/tests",
            "verify implementation",
            "validate submission flow end-to-end",
            "check responsive behavior",
            "confirm no unapproved scope",
        ]
        if any(p in t for p in qa_phrases):
            return "qa", 0.98

        # ---- Project setup / tooling ----
        setup_phrases = [
            "initialize project structure",
            "development environment",
            "initialize repository",
            "project setup",
            "setup project",
            "apply repository quality rules",
            "formatter, linting, tests where applicable",
        ]
        if any(p in t for p in setup_phrases):
            return "setup", 0.96

        # ---- Frontend implementation ----
        frontend_phrases = [
            "page layout",
            "design system",
            "implement `about` section",
            "implement `certifications` section",
            "implement `contact` section",
            "implement `experience` section",
            "implement `hero` section",
            "implement `projects` section",
            "implement `skills` section",
            "apply confirmed `dark` theme",
            "reference aspects as inspiration",
            "implement form fields",
            "client-side validation",
            "success and failure states",
            "responsive ui",
            "animation",
            "typography",
        ]
        if any(p in t for p in frontend_phrases):
            return "frontend", 0.97

        # General frontend token fallback.
        frontend_terms = [
            "frontend", "ui", "ux", "layout", "responsive", "component",
            "section", "theme", "visual", "design", "hero",
        ]
        front_hits = sum(1 for term in frontend_terms if term in t)

        # ---- Backend implementation ----
        backend_phrases = [
            "submit form data",
            "server-side",
            "backend",
            "api endpoint",
            "database",
            "webhook",
            "email delivery",
            "persist data",
        ]
        if any(p in t for p in backend_phrases):
            return "backend", 0.97

        backend_terms = [
            "server", "api", "database", "db", "endpoint", "webhook",
            "email", "submission", "persist",
        ]
        back_hits = sum(1 for term in backend_terms if term in t)

        if front_hits and not back_hits:
            return "frontend", 0.92
        if back_hits and not front_hits:
            return "backend", 0.92
        if front_hits and back_hits:
            return ("frontend", 0.78) if front_hits >= back_hits else ("backend", 0.78)

        # ---- Architecture ----
        architecture_phrases = [
            "architecture",
            "arsitektur",
            "system design",
            "repository architecture",
            "framework selection",
            "tooling selection",
        ]
        if any(p in t for p in architecture_phrases):
            return "architecture", 0.92

        return "general_engineering", 0.60
