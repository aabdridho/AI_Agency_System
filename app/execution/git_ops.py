import re
import subprocess
from pathlib import Path


class GitOps:
    def __init__(self, repo: str | Path):
        self.repo = Path(repo)

    def _run(self, args, *, check=True):
        return subprocess.run(
            args,
            cwd=self.repo,
            check=check,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def is_git_repo(self) -> bool:
        result = self._run(["git", "rev-parse", "--is-inside-work-tree"], check=False)
        return result.returncode == 0 and result.stdout.strip() == "true"

    def ensure_repo(self):
        if not self.is_git_repo():
            self._run(["git", "init"])

    def has_commits(self) -> bool:
        result = self._run(["git", "rev-parse", "--verify", "HEAD"], check=False)
        return result.returncode == 0

    def has_changes(self) -> bool:
        result = self._run(["git", "status", "--porcelain"], check=True)
        return bool(result.stdout.strip())


    def changed_paths(self) -> list[str]:
        result = self._run(["git", "status", "--porcelain"], check=True)
        paths: list[str] = []
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            raw = line[3:].strip()
            # Handle rename syntax "old -> new" conservatively by keeping target.
            if " -> " in raw:
                raw = raw.split(" -> ", 1)[1]
            paths.append(raw.replace("\\", "/"))
        return paths

    def clean_known_generated_drift(self) -> list[str]:
        """
        Restore only tracked files that are known to be framework-generated and
        safe to regenerate. Never touches arbitrary source/config changes.
        """
        generated = {"next-env.d.ts"}
        changed = self.changed_paths()
        safe = [p for p in changed if p in generated]
        unsafe = [p for p in changed if p not in generated]

        if unsafe or not safe:
            return []

        for path in safe:
            # Only restore tracked files. If untracked, leave it for the normal
            # dirty-repo guard to reject.
            tracked = self._run(["git", "ls-files", "--error-unmatch", path], check=False)
            if tracked.returncode != 0:
                return []
        self._run(["git", "restore", "--"] + safe)
        return safe

    def ensure_baseline_commit(self):
        """
        Ensure there is a committed baseline before task branches are created.
        Uses one-off local commit identity flags so global Git config is untouched.
        """
        self.ensure_repo()

        if not self.has_commits():
            self._run(["git", "add", "-A"])
            self._run([
                "git",
                "-c", "user.name=AI Agency",
                "-c", "user.email=ai-agency@local",
                "commit",
                "--allow-empty",
                "-m", "chore: execution baseline",
            ])
            return

        # Existing repo must be clean before automation starts. A very small
        # allow-list of framework-generated tracked drift can be restored safely.
        if self.has_changes():
            restored = self.clean_known_generated_drift()
            if restored:
                print("↺ Restored generated drift: " + ", ".join(restored))

        if self.has_changes():
            changed = ", ".join(self.changed_paths()[:10])
            raise RuntimeError(
                "Repository memiliki perubahan yang belum di-commit. "
                "Commit/stash perubahan tersebut sebelum real execution. "
                f"Changed paths: {changed}"
            )

    def sanitize_branch(self, task_id: str, task_text: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", task_text.lower()).strip("-")
        slug = slug[:48] or "task"
        return f"ai/{task_id.lower()}-{slug}"

    def integration_branch(self, project_name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", project_name.lower()).strip("-") or "project"
        return f"ai/integration/{slug}"

    def repair_branch(self, task_id: str, attempt: int) -> str:
        task = re.sub(r"[^a-z0-9]+", "-", task_id.lower()).strip("-") or "qa"
        return f"ai/repair/{task}-attempt-{attempt}"

    def current_branch(self) -> str:
        result = self._run(["git", "branch", "--show-current"])
        return result.stdout.strip()

    def head_sha(self) -> str:
        result = self._run(["git", "rev-parse", "HEAD"])
        return result.stdout.strip()

    def ref_sha(self, ref: str) -> str:
        result = self._run(["git", "rev-parse", ref])
        return result.stdout.strip()

    def is_ancestor(self, ancestor: str, descendant: str) -> bool:
        result = self._run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            check=False,
        )
        return result.returncode == 0

    def branch_exists(self, branch: str) -> bool:
        result = self._run(
            ["git", "show-ref", "--verify", f"refs/heads/{branch}"],
            check=False,
        )
        return result.returncode == 0

    def task_already_merged(self, task_branch: str, integration_branch: str) -> bool:
        """
        True only when the task branch has its own commit(s) beyond the integration
        base history and its tip is already contained in integration.

        Old placeholder branches that still point at the execution baseline are
        not treated as completed.
        """
        if not self.branch_exists(task_branch) or not self.branch_exists(integration_branch):
            return False

        task_sha = self.ref_sha(task_branch)
        integration_sha = self.ref_sha(integration_branch)

        if not self.is_ancestor(task_sha, integration_branch):
            return False

        # A task branch that is simply an ancestor/base (e.g. old baseline pointer)
        # must not be interpreted as a completed task. Require its subject to match
        # the orchestrator's task commit convention.
        subject = self._run(
            ["git", "log", "-1", "--format=%s", task_branch]
        ).stdout.strip()

        return subject.startswith("TASK-")

    def create_or_reset_branch_from(self, branch: str, base: str):
        self._run(["git", "checkout", base])
        self._run(["git", "checkout", "-B", branch, base])

    def create_or_switch_integration(self, branch: str):
        # Create from current HEAD on first run; otherwise switch to existing branch.
        exists = self._run(["git", "show-ref", "--verify", f"refs/heads/{branch}"], check=False)
        if exists.returncode == 0:
            self._run(["git", "checkout", branch])
        else:
            self._run(["git", "checkout", "-b", branch])

    def working_tree_clean(self) -> bool:
        proc = self._run(["git", "status", "--porcelain"])
        if proc.returncode != 0:
            raise RuntimeError(
                "Unable to inspect Git working tree during recovery."
            )
        return not proc.stdout.strip()

    def recover_interrupted_task(
        self,
        active_branch: str,
        integration_branch: str,
    ) -> None:
        """
        Recover only transient work from an interrupted active task.

        The integration branch is never reset. The active task working tree is
        discarded, then execution returns to the existing integration branch.
        """
        current = self.current_branch()

        if current != active_branch:
            raise RuntimeError(
                "Interrupted-task recovery refused because the current branch "
                f"is {current!r}, expected {active_branch!r}."
            )

        if not self.branch_exists(integration_branch):
            raise RuntimeError(
                "Interrupted-task recovery refused because integration branch "
                f"{integration_branch!r} does not exist."
            )

        reset = self._run(["git", "reset", "--hard", "HEAD"])
        if reset.returncode != 0:
            raise RuntimeError(
                "Failed to discard tracked partial task changes during "
                "interrupt recovery."
            )

        clean = self._run(["git", "clean", "-fd"])
        if clean.returncode != 0:
            raise RuntimeError(
                "Failed to discard untracked partial task changes during "
                "interrupt recovery."
            )

        switch = self._run(["git", "switch", integration_branch])
        if switch.returncode != 0:
            raise RuntimeError(
                "Failed to return to integration branch during interrupt "
                "recovery."
            )

        if self.current_branch() != integration_branch:
            raise RuntimeError(
                "Interrupt recovery completed on an unexpected Git branch."
            )

        if not self.working_tree_clean():
            raise RuntimeError(
                "Interrupt recovery left the integration working tree dirty."
            )

    def reset_hard_to(self, ref: str):
        self._run(["git", "reset", "--hard", ref])
        self._run(["git", "clean", "-fd"])

    def commit_all(self, message: str) -> bool:
        self._run(["git", "add", "-A"])
        if not self.has_changes():
            return False
        self._run([
            "git",
            "-c", "user.name=AI Agency",
            "-c", "user.email=ai-agency@local",
            "commit",
            "-m", message,
        ])
        return True

    def merge_no_ff(self, branch: str, message: str):
        self._run([
            "git",
            "-c", "user.name=AI Agency",
            "-c", "user.email=ai-agency@local",
            "merge",
            "--no-ff",
            branch,
            "-m", message,
        ])
