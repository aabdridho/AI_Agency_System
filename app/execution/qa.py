import json
import re
import shutil
from app.command_resolver import resolve_node_cli
import subprocess
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace


@dataclass(frozen=True)
class QAProfile:
    name: str
    description: str


class DeterministicQA:
    """
    V0.7 task-aware QA.

    Instead of blindly running the exact same validation suite for every QA task,
    the task text selects a deterministic profile:
      - submission_e2e
      - requirements_audit
      - validation
      - responsive_audit
      - scope_audit
      - generic
    """

    def _npm_scripts(self, repo: Path) -> dict:
        package_json = repo / "package.json"
        if not package_json.exists():
            return {}
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
            return data.get("scripts", {}) or {}
        except Exception:
            return {}

    def profile_for(self, task_text: str) -> QAProfile:
        t = task_text.lower().strip()

        if "submission flow end-to-end" in t or "end-to-end" in t or "e2e" in t:
            return QAProfile(
                "submission_e2e",
                "Target the confirmed submission flow and its integration boundary.",
            )
        if "verify implementation against every confirmed requirement" in t:
            return QAProfile(
                "requirements_audit",
                "Audit implementation/task completion against confirmed requirements.",
            )
        if "deterministic validation" in t or "lint/tests" in t:
            return QAProfile(
                "validation",
                "Run repository-wide deterministic engineering validation.",
            )
        if "responsive behavior" in t:
            return QAProfile(
                "responsive_audit",
                "Check that responsive implementation evidence exists and remains buildable.",
            )
        if "no unapproved scope" in t or "scope" in t:
            return QAProfile(
                "scope_audit",
                "Audit common unapproved-scope indicators against project documentation.",
            )
        return QAProfile("generic", "Run the repository's deterministic validation suite.")

    def _npm_cmd(self) -> str | None:
        return resolve_node_cli("npm")

    def _core_node_commands(self, repo: Path) -> list[list[str]]:
        npm_cmd = self._npm_cmd()
        if not npm_cmd or not (repo / "package.json").exists():
            return []

        scripts = self._npm_scripts(repo)
        commands: list[list[str]] = []
        if "lint" in scripts:
            commands.append([npm_cmd, "run", "lint"])
        if "typecheck" in scripts:
            commands.append([npm_cmd, "run", "typecheck"])
        if "test" in scripts:
            commands.append([npm_cmd, "test"])
        if "build" in scripts:
            commands.append([npm_cmd, "run", "build"])
        return commands

    def detect_commands(self, repo: str | Path, task_text: str | None = None) -> list[list[str]]:
        repo = Path(repo)
        profile = self.profile_for(task_text or "")
        npm_cmd = self._npm_cmd()
        scripts = self._npm_scripts(repo)
        commands: list[list[str]] = []

        if (repo / "package.json").exists() and npm_cmd:
            if profile.name == "submission_e2e":
                # Prefer dedicated project scripts where they exist.
                for candidate in ("test:e2e", "e2e", "test:integration", "test:contact"):
                    if candidate in scripts:
                        commands.append([npm_cmd, "run", candidate])
                        break
                else:
                    # Fall back to the repository test suite; specialized static
                    # coverage checks below ensure contact/submission evidence exists.
                    if "test" in scripts:
                        commands.append([npm_cmd, "test"])
                if "typecheck" in scripts:
                    commands.append([npm_cmd, "run", "typecheck"])

            elif profile.name == "validation":
                commands.extend(self._core_node_commands(repo))

            elif profile.name in {"requirements_audit", "responsive_audit", "scope_audit"}:
                # These profiles have dedicated deterministic audits. Build/typecheck
                # protects against source-level audits passing on broken code.
                if "typecheck" in scripts:
                    commands.append([npm_cmd, "run", "typecheck"])
                if "build" in scripts:
                    commands.append([npm_cmd, "run", "build"])

            else:
                commands.extend(self._core_node_commands(repo))

        # Python projects: generic/validation profile keeps pytest support.
        if profile.name in {"generic", "validation"} and (
            (repo / "pyproject.toml").exists()
            or (repo / "requirements.txt").exists()
            or (repo / "pytest.ini").exists()
        ) and shutil.which("python"):
            commands.append(["python", "-m", "pytest", "-q"])

        return commands

    def _synthetic(self, name: str, ok: bool, message: str):
        return (
            ["internal-audit", name],
            SimpleNamespace(
                returncode=0 if ok else 1,
                stdout=message if ok else "",
                stderr="" if ok else message,
            ),
        )

    def _source_files(self, repo: Path) -> list[Path]:
        # Support both framework-style repositories and plain/static sites.
        # Generated client projects may keep implementation source under
        # assets/ or directly at repository root.
        roots = [
            repo / "src",
            repo / "app",
            repo / "pages",
            repo / "components",
            repo / "tests",
            repo / "assets",
            repo / "public",
        ]
        suffixes = {
            ".ts",
            ".tsx",
            ".js",
            ".jsx",
            ".css",
            ".scss",
            ".html",
            ".mjs",
            ".py",
        }

        files: list[Path] = []

        for base in roots:
            if not base.exists():
                continue
            for path in base.rglob("*"):
                if path.is_file() and path.suffix.lower() in suffixes:
                    files.append(path)

        # Plain HTML/CSS/JS projects commonly keep entry files at repo root.
        for path in repo.iterdir():
            if path.is_file() and path.suffix.lower() in suffixes:
                files.append(path)

        # Preserve deterministic ordering and avoid duplicate paths.
        return sorted(set(files))

    def _combined_source(self, repo: Path) -> str:
        chunks = []
        for path in self._source_files(repo):
            try:
                chunks.append(path.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                continue
        return "\n".join(chunks).lower()

    def _submission_audit(self, repo: Path):
        source = self._combined_source(repo)
        test_text = "\n".join(
            p.read_text(encoding="utf-8", errors="replace")
            for p in (repo / "tests").glob("*")
            if p.is_file()
        ).lower() if (repo / "tests").exists() else ""

        route_evidence = (
            "/api/contact" in source
            or "api/contact" in source
            or "contact" in source and ("post" in source or "submit" in source)
        )
        fields = all(field in source for field in ("name", "email", "company", "message"))
        test_evidence = "contact" in test_text and (
            "submission" in test_text or "email" in test_text or "provider" in test_text
        )

        ok = route_evidence and fields and test_evidence
        detail = (
            f"submission route/handler evidence={route_evidence}; "
            f"required fields evidence={fields}; targeted test evidence={test_evidence}"
        )
        return self._synthetic("submission_e2e_coverage", ok, detail)

    def _requirements_audit(self, repo: Path):
        req = repo / "docs" / "requirement.md"
        task = repo / "docs" / "task.md"
        if not req.exists() or not task.exists():
            return self._synthetic(
                "requirements_audit",
                False,
                "docs/requirement.md and docs/task.md are required for requirement verification.",
            )

        req_text = req.read_text(encoding="utf-8", errors="replace")
        task_text = task.read_text(encoding="utf-8", errors="replace")
        source = self._combined_source(repo)

        approved = "CLIENT_APPROVED" in req_text and "Ready for development: True" in req_text

        # Only implementation work before the QA heading must be complete.
        # Validation/verification tasks are QA work even when an older task.md
        # happens to place them under another heading (for example Contact Form).
        implementation_part = task_text.split("## QA", 1)[0]
        unchecked_all = re.findall(
            r"^- \[ \] (.+)$",
            implementation_part,
            flags=re.MULTILINE,
        )
        qa_like = re.compile(
            r"^(validate|verify|check|confirm|run\s+deterministic)\b",
            flags=re.IGNORECASE,
        )
        unchecked = [item for item in unchecked_all if not qa_like.search(item.strip())]

        required_sections = []
        m = re.search(r"\*\*required_sections\*\*:\s*(.+)", req_text)
        if m:
            required_sections = [x.strip().lower() for x in m.group(1).split(",") if x.strip()]
        sections_present = all(section in source for section in required_sections)

        contact_fields = []
        m = re.search(r"\*\*contact_fields\*\*:\s*(.+)", req_text)
        if m:
            contact_fields = [x.strip().lower() for x in m.group(1).split(",") if x.strip()]
        fields_present = all(field in source for field in contact_fields)

        ok = approved and not unchecked and sections_present and fields_present
        detail = (
            f"approved_gate={approved}; unchecked_implementation_tasks={len(unchecked)}; "
            f"required_sections_present={sections_present}; contact_fields_present={fields_present}"
        )
        if unchecked:
            detail += "; unchecked=" + " | ".join(unchecked[:8])
        return self._synthetic("requirements_audit", ok, detail)

    def _responsive_audit(self, repo: Path):
        source = self._combined_source(repo)
        markers = [
            "@media",
            "clamp(",
            "minmax(",
            "grid-template-columns",
            "flex-wrap",
            "max-width",
            "min-width",
            "sm:",
            "md:",
            "lg:",
        ]
        evidence = [marker for marker in markers if marker in source]
        ok = len(evidence) >= 2
        detail = (
            "responsive implementation markers: "
            + (", ".join(evidence) if evidence else "none")
            + f" (need at least 2 distinct markers; found {len(evidence)})"
        )
        return self._synthetic("responsive_source_audit", ok, detail)

    def _scope_audit(self, repo: Path):
        backend = repo / "docs" / "backend.md"
        req = repo / "docs" / "requirement.md"

        doc_text = ""
        for p in (backend, req):
            if p.exists():
                doc_text += "\n" + p.read_text(encoding="utf-8", errors="replace").lower()

        package = {}
        package_json = repo / "package.json"
        if package_json.exists():
            try:
                package = json.loads(package_json.read_text(encoding="utf-8"))
            except Exception:
                package = {}

        dependencies = {
            str(name).lower()
            for section in ("dependencies", "devDependencies")
            for name in (package.get(section, {}) or {}).keys()
        }

        # Inspect implementation file paths and non-content implementation source.
        # Do NOT treat portfolio copy/docs mentioning "database", "auth", etc. as
        # implementation evidence; a Data Engineering portfolio legitimately talks
        # about databases as subject matter.
        implementation_files: list[Path] = []
        for base_name in ("src", "app", "pages", "components", "lib"):
            base = repo / base_name
            if not base.exists():
                continue
            for path in base.rglob("*"):
                if not path.is_file():
                    continue
                rel = path.relative_to(repo).as_posix().lower()
                if "/content/" in f"/{rel}/":
                    continue
                if path.suffix.lower() not in {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py"}:
                    continue
                implementation_files.append(path)

        rel_paths = [p.relative_to(repo).as_posix().lower() for p in implementation_files]
        source = "\n".join(
            p.read_text(encoding="utf-8", errors="replace").lower()
            for p in implementation_files
        )

        forbidden = {
            "authentication": (
                {"next-auth", "@auth/core", "@clerk/nextjs", "@auth0/nextjs-auth0", "lucia"},
                ("/auth/", "/login", "/signin", "/signup", "/register"),
                ("from \"next-auth", "from '@clerk", "from \"@clerk", "auth0", "clerkprovider"),
            ),
            "database": (
                {"prisma", "@prisma/client", "drizzle-orm", "mongoose", "pg", "mysql2", "sequelize", "knex", "better-sqlite3"},
                ("/prisma/", "/db/", "/database/", "schema.prisma"),
                ("new prisma", "prismaclient", "drizzle(", "mongoose.connect", "createpool(", "new sequelize"),
            ),
            "crm": (
                {"@hubspot/api-client", "jsforce"},
                ("/crm/", "/hubspot/", "/salesforce/"),
                ("hubspot", "salesforce", "jsforce"),
            ),
            "admin": (
                set(),
                ("/admin/", "/admin.", "/dashboard/admin"),
                ("admin dashboard", "adminpanel", "admin panel"),
            ),
        }

        violations = []
        evidence: dict[str, list[str]] = {}

        for feature, (dep_markers, path_markers, source_markers) in forbidden.items():
            explicitly_out = "out of scope" in doc_text and feature in doc_text
            if not explicitly_out:
                continue

            hits: list[str] = []
            dep_hits = sorted(dep_markers & dependencies)
            if dep_hits:
                hits.extend(f"dependency:{name}" for name in dep_hits)

            for path in rel_paths:
                if any(marker in f"/{path}" for marker in path_markers):
                    hits.append(f"path:{path}")

            for marker in source_markers:
                if marker in source:
                    hits.append(f"source:{marker}")

            if hits:
                violations.append(feature)
                evidence[feature] = sorted(set(hits))[:8]

        ok = not violations
        if ok:
            detail = "no structural/dependency evidence of documented out-of-scope features detected"
        else:
            parts = [
                f"{feature} ({', '.join(evidence[feature])})"
                for feature in violations
            ]
            detail = "possible out-of-scope implementation evidence: " + "; ".join(parts)

        return self._synthetic("scope_audit", ok, detail)

    def _run_commands(self, repo: Path, commands: list[list[str]]):
        results = []
        for cmd in commands:
            proc = subprocess.run(
                cmd,
                cwd=repo,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            results.append((cmd, proc))
        return results

    def run(self, repo: str | Path, task_text: str | None = None):
        repo = Path(repo)
        profile = self.profile_for(task_text or "")
        results = self._run_commands(repo, self.detect_commands(repo, task_text))

        if profile.name == "submission_e2e":
            results.append(self._submission_audit(repo))
        elif profile.name == "requirements_audit":
            results.append(self._requirements_audit(repo))
        elif profile.name == "responsive_audit":
            results.append(self._responsive_audit(repo))
        elif profile.name == "scope_audit":
            results.append(self._scope_audit(repo))

        return results
