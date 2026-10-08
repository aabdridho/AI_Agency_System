import inspect
from pathlib import Path

from app.agents import (
    AgentHeartbeat,
    AgentRegistry,
    AgentStateUpdate,
    AgentStatus,
    registry as default_agent_registry,
)
from app.execution.adapters import ClaudeCodeAdapter, CodexAdapter
from app.execution.git_ops import GitOps
from app.execution.models import ExecutionRecord, ExecutionReport
from app.execution.prompt_builder import TaskPromptBuilder
from app.execution.qa import DeterministicQA
from app.execution.usage import UsageLedger, parse_usage
from app.routing.models import RoutingPlan


class ExecutionEngine:
    OWNER_AGENT_IDS = {
        "codex": "codex",
        "claude_code": "claude-code",
        "deterministic_qa": "deterministic-qa",
    }

    def __init__(
        self,
        agent_registry: AgentRegistry | None = None,
        usage_ledger: UsageLedger | None = None,
    ):
        self.prompt_builder = TaskPromptBuilder()
        self.adapters = {
            "claude_code": ClaudeCodeAdapter(),
            "codex": CodexAdapter(),
        }
        self.qa = DeterministicQA()

        self.agent_registry = (
            agent_registry
            if agent_registry is not None
            else default_agent_registry
        )
        self.usage_ledger = usage_ledger

    def _run_adapter(
        self,
        adapter,
        root: Path,
        prompt: str,
        *,
        model: str | None,
        effort: str | None,
    ):
        """
        Backward-compatible adapter invocation.

        Native V0.13 adapters accept model/effort, while existing test
        doubles and third-party adapters may still expose the older
        run(repo, prompt, stream=True) signature.
        """
        params = inspect.signature(adapter.run).parameters
        kwargs = {"stream": True}

        if "model" in params:
            kwargs["model"] = model

        if "effort" in params:
            kwargs["effort"] = effort

        return adapter.run(
            root,
            prompt,
            **kwargs,
        )

    def _record_usage(
        self,
        *,
        proc,
        owner: str,
        project_name: str,
        task_id: str,
        phase: str,
        requested_model: str | None = None,
        requested_effort: str | None = None,
        goat_tier: str | None = None,
    ) -> None:
        if self.usage_ledger is None:
            return

        try:
            metrics = parse_usage(
                owner,
                getattr(proc, "stdout", "") or "",
            )

            if metrics is None:
                return

            updates = {}

            # Prefer a provider-reported canonical model. When the CLI does
            # not report one (Codex 0.160.1), attribution falls back to the
            # explicit model that the orchestrator actually requested.
            if not metrics.model and requested_model:
                updates["model"] = requested_model
                updates["model_source"] = "execution_request"

            if requested_effort:
                updates["requested_effort"] = requested_effort

            if goat_tier:
                updates["goat_tier"] = goat_tier

            if updates:
                metrics = metrics.model_copy(update=updates)

            self.usage_ledger.append(
                project_name=project_name,
                task_id=task_id,
                owner=owner,
                phase=phase,
                metrics=metrics,
            )
        except Exception:
            # Observability must never break execution.
            return

    def _agent_id(self, owner: str) -> str | None:
        return self.OWNER_AGENT_IDS.get(owner)

    def _agent_session(
        self,
        project_name: str,
        task_id: str,
        phase: str = "task",
    ) -> str:
        return f"{phase}:{project_name}:{task_id}"

    def _set_agent_state(
        self,
        owner: str,
        status: AgentStatus,
        *,
        project_name: str | None = None,
        task_id: str | None = None,
        session_id: str | None = None,
    ) -> None:
        agent_id = self._agent_id(owner)

        if not agent_id:
            return

        try:
            self.agent_registry.update_state(
                agent_id,
                AgentStateUpdate(
                    status=status,
                    current_task=task_id,
                    project=project_name,
                    session_id=session_id,
                ),
            )
        except Exception:
            return

    def _agent_start(
        self,
        owner: str,
        *,
        project_name: str,
        task_id: str,
        phase: str = "task",
    ) -> None:
        session_id = self._agent_session(
            project_name,
            task_id,
            phase,
        )

        self._set_agent_state(
            owner,
            AgentStatus.RUNNING,
            project_name=project_name,
            task_id=task_id,
            session_id=session_id,
        )

        agent_id = self._agent_id(owner)

        if not agent_id:
            return

        try:
            self.agent_registry.heartbeat(
                agent_id,
                AgentHeartbeat(
                    current_task=task_id,
                    project=project_name,
                    session_id=session_id,
                ),
            )
        except Exception:
            return

    def _agent_waiting(
        self,
        owner: str,
        *,
        project_name: str,
        task_id: str,
        phase: str = "task",
    ) -> None:
        self._set_agent_state(
            owner,
            AgentStatus.WAITING,
            project_name=project_name,
            task_id=task_id,
            session_id=self._agent_session(
                project_name,
                task_id,
                phase,
            ),
        )

    def _agent_error(
        self,
        owner: str,
        *,
        project_name: str,
        task_id: str,
        phase: str = "task",
    ) -> None:
        self._set_agent_state(
            owner,
            AgentStatus.ERROR,
            project_name=project_name,
            task_id=task_id,
            session_id=self._agent_session(
                project_name,
                task_id,
                phase,
            ),
        )

    def _agent_idle(self, owner: str) -> None:
        self._set_agent_state(
            owner,
            AgentStatus.IDLE,
        )

    def _command_preview(self, owner: str, prompt: str) -> str:
        if owner == "deterministic_qa":
            return "deterministic QA commands detected from repository"
        adapter = self.adapters.get(owner)

        if not adapter:
            return f"unsupported owner: {owner}"

        build_command = getattr(
            adapter,
            "build_command",
            None,
        )

        if not callable(build_command):
            binary = getattr(
                adapter,
                "binary",
                owner,
            )
            return f"{binary} <task-context>"

        cmd = build_command(prompt)

        return " ".join(cmd[:2]) + " <task-context>"

    def _run_qa(self, root: Path, task_text: str):
        # Backward-compatible with simple/custom QA doubles used by tests and
        # third-party integrations that still expose run(repo) only.
        try:
            return self.qa.run(root, task_text)
        except TypeError as exc:
            try:
                return self.qa.run(root)
            except TypeError:
                raise exc

    def _qa_profile_name(self, task_text: str) -> str:
        profile_for = getattr(self.qa, "profile_for", None)
        if callable(profile_for):
            return profile_for(task_text).name
        return "generic"

    def _qa_failed(self, results) -> bool:
        return any(proc.returncode != 0 for _, proc in results)

    def _qa_output(self, results) -> tuple[str, str]:
        stdout = "\n".join((proc.stdout or "") for _, proc in results)
        stderr = "\n".join((proc.stderr or "") for _, proc in results)
        return stdout, stderr

    def _qa_failure_context(self, results, limit: int = 16000) -> str:
        chunks = []
        for cmd, proc in results:
            if proc.returncode == 0:
                continue
            chunks.append(
                "\n".join(
                    [
                        f"$ {' '.join(cmd)}",
                        f"exit_code={proc.returncode}",
                        "--- stdout ---",
                        (proc.stdout or "").strip(),
                        "--- stderr ---",
                        (proc.stderr or "").strip(),
                    ]
                )
            )
        text = "\n\n".join(chunks).strip()
        if len(text) > limit:
            text = text[-limit:]
            text = "[truncated to most recent failure output]\n" + text
        return text

    def _build_qa_repair_prompt(self, root: Path, task_text: str, results) -> str:
        failure_context = self._qa_failure_context(results)
        base = self.prompt_builder.build(
            root,
            f"Repair the deterministic QA failure discovered while validating: {task_text}",
        )
        return (
            base
            + "\n\nQA REPAIR CONTRACT:\n"
            + "- Diagnose the supplied deterministic QA failure and make the smallest code/config change that fixes it.\n"
            + "- Do not add client-facing scope or redesign unrelated features.\n"
            + "- Do not weaken, delete, disable, or bypass tests, lint rules, type checks, or build validation merely to make QA pass.\n"
            + "- Preserve already approved requirements and previously completed work.\n"
            + "- Run focused validation when useful, but leave all final changes in the working tree for the orchestrator.\n"
            + "\nDETERMINISTIC QA FAILURE OUTPUT:\n"
            + failure_context
        )

    def _attempt_qa_repair(
        self,
        *,
        root: Path,
        git: GitOps,
        integration_branch: str,
        task_id: str,
        task_text: str,
        project_name: str,
        results,
        attempt: int,
        primary_owner: str = "codex",
        allow_fallback: bool = True,
    ) -> dict:
        repair_branch = git.repair_branch(task_id, attempt)
        prompt = self._build_qa_repair_prompt(root, task_text, results)
        base_sha = git.ref_sha(integration_branch)

        owners = [primary_owner]
        fallback_owner = "claude_code" if primary_owner == "codex" else "codex"
        if allow_fallback and fallback_owner not in owners:
            owners.append(fallback_owner)

        last_proc = None
        used_owner = None

        for owner_index, owner in enumerate(owners):
            adapter = self.adapters.get(owner)
            if not adapter or not adapter.available():
                continue

            # Every repair attempt starts from the current clean integration state.
            git.create_or_reset_branch_from(repair_branch, integration_branch)
            print(f"â†’ QA repair attempt {attempt} with {owner}...")

            self._agent_start(
                owner,
                project_name=project_name,
                task_id=task_id,
                phase=f"qa-repair-{attempt}",
            )

            try:
                repair_model = (
                    "gpt-6.1-sol"
                    if owner == "codex"
                    else "sonnet"
                )
                repair_effort = "medium"

                proc = self._run_adapter(
                    adapter,
                    root,
                    prompt,
                    model=repair_model,
                    effort=repair_effort,
                )
            except Exception:
                self._agent_error(
                    owner,
                    project_name=project_name,
                    task_id=task_id,
                    phase=f"qa-repair-{attempt}",
                )
                raise

            self._record_usage(
                proc=proc,
                owner=owner,
                project_name=project_name,
                task_id=task_id,
                phase=f"qa-repair-{attempt}",
                requested_model=repair_model,
                requested_effort=repair_effort,
            )

            last_proc = proc
            used_owner = owner

            changed = proc.returncode == 0 and git.has_changes()
            if not changed:
                reason = (
                    f"return code {proc.returncode}"
                    if proc.returncode != 0
                    else "repair returned success but produced no repository changes"
                )
                print(f"â†’ QA repair owner {owner} failed ({reason}).")

                self._agent_error(
                    owner,
                    project_name=project_name,
                    task_id=task_id,
                    phase=f"qa-repair-{attempt}",
                )

                git.reset_hard_to(integration_branch)
                if owner_index < len(owners) - 1:
                    continue
                break

            committed = git.commit_all(
                f"REPAIR {task_id}: deterministic QA failure"
            )
            if not committed:
                self._agent_error(
                    owner,
                    project_name=project_name,
                    task_id=task_id,
                    phase=f"qa-repair-{attempt}",
                )
                git.reset_hard_to(integration_branch)
                break

            repair_commit_sha = git.head_sha()
            git.create_or_switch_integration(integration_branch)
            git.merge_no_ff(
                repair_branch,
                f"merge REPAIR {task_id}: deterministic QA failure",
            )

            merged = (
                git.head_sha() != base_sha
                and git.is_ancestor(repair_commit_sha, integration_branch)
            )
            if not merged:
                self._agent_error(
                    owner,
                    project_name=project_name,
                    task_id=task_id,
                    phase=f"qa-repair-{attempt}",
                )

                return {
                    "success": False,
                    "owner": used_owner,
                    "branch": repair_branch,
                    "stdout": getattr(last_proc, "stdout", "") or "",
                    "stderr": "QA repair commit could not be verified in integration.",
                }

            print(f"âœ“ QA repair merged into {integration_branch}")

            self._agent_idle(owner)

            return {
                "success": True,
                "owner": used_owner,
                "branch": repair_branch,
                "stdout": getattr(last_proc, "stdout", "") or "",
                "stderr": getattr(last_proc, "stderr", "") or "",
            }

        git.create_or_switch_integration(integration_branch)
        return {
            "success": False,
            "owner": used_owner,
            "branch": repair_branch,
            "stdout": getattr(last_proc, "stdout", "") if last_proc else "",
            "stderr": (
                getattr(last_proc, "stderr", "") if last_proc else
                "No available repair owner."
            ),
        }

    def required_binaries(self, plan: RoutingPlan) -> set[str]:
        binaries = {"git"}
        for d in plan.decisions:
            adapter = self.adapters.get(d.primary_owner)
            if adapter:
                binaries.add(adapter.binary)
        return binaries

    def execute(
        self,
        plan: RoutingPlan,
        project_root: str | Path,
        *,
        dry_run: bool = True,
        allow_escalation: bool = True,
        auto_repair_qa: bool = True,
        max_qa_repair_cycles: int = 2,
    ) -> ExecutionReport:
        root = Path(project_root)
        git = GitOps(root)
        integration_branch = git.integration_branch(plan.project_name)

        if not dry_run:
            git.ensure_baseline_commit()
            git.create_or_switch_integration(integration_branch)

        records = []

        total = len(plan.decisions)
        qa_repairs_used = 0

        # Fail fast before spending model calls if the project working tree is
        # not writable by the orchestration process.
        if not dry_run:
            probe = root / ".ai_agency_write_probe"
            try:
                probe.write_text("write-ok", encoding="utf-8")
                probe.unlink()
            except Exception as exc:
                raise RuntimeError(
                    f"Project workspace is not writable: {root} ({exc})"
                ) from exc

        for index, decision in enumerate(plan.decisions, start=1):
            task_branch = git.sanitize_branch(decision.task_id, decision.task_text)
            prompt = self.prompt_builder.build(root, decision.task_text)

            if not dry_run:
                print("\n" + "=" * 72)
                print(f"[{index}/{total}] {decision.task_id} â€” {decision.task_text}")
                print(f"Owner: {decision.primary_owner}")
                print("=" * 72)

            # Safe resume: if an implementation task already has a verified
            # task commit contained in integration, do not execute it again.
            if (
                not dry_run
                and decision.primary_owner != "deterministic_qa"
                and git.task_already_merged(task_branch, integration_branch)
            ):
                print(f"â†· {decision.task_id} already merged; skipping.")
                records.append(
                    ExecutionRecord(
                        task_id=decision.task_id,
                        owner=decision.primary_owner,
                        branch=task_branch,
                        status="skipped",
                        command_preview="already merged into integration",
                        return_code=0,
                        stdout="Task commit already exists in and is contained by the integration branch.",
                    )
                )
                continue

            if dry_run:
                branch = integration_branch if decision.primary_owner == "deterministic_qa" else task_branch
                records.append(
                    ExecutionRecord(
                        task_id=decision.task_id,
                        owner=decision.primary_owner,
                        branch=branch,
                        status="dry_run",
                        command_preview=self._command_preview(decision.primary_owner, prompt),
                    )
                )
                continue

            # QA runs against the cumulative integration branch.
            if decision.primary_owner == "deterministic_qa":
                git.create_or_switch_integration(integration_branch)

                self._agent_start(
                    "deterministic_qa",
                    project_name=plan.project_name,
                    task_id=decision.task_id,
                    phase="qa",
                )

                try:
                    results = self._run_qa(
                        root,
                        decision.task_text,
                    )
                except Exception:
                    self._agent_error(
                        "deterministic_qa",
                        project_name=plan.project_name,
                        task_id=decision.task_id,
                        phase="qa",
                    )
                    raise

                if not results:
                    self._agent_error(
                        "deterministic_qa",
                        project_name=plan.project_name,
                        task_id=decision.task_id,
                        phase="qa",
                    )

                    records.append(
                        ExecutionRecord(
                            task_id=decision.task_id,
                            owner=decision.primary_owner,
                            branch=integration_branch,
                            status="failed",
                            command_preview="no deterministic QA command detected",
                            return_code=2,
                            stderr=(
                                "No executable deterministic QA command was detected. "
                                "QA cannot be marked successful without actually running a check."
                            ),
                        )
                    )
                    print("✗ QA blocked: no deterministic command detected.")

                    # Failure is already preserved in ExecutionRecord.
                    # Agent live state must not remain stale ERROR forever.
                    self._agent_idle("deterministic_qa")

                    continue

                qa_profile = self._qa_profile_name(decision.task_text)
                print(f"QA profile: {qa_profile}")
                initial_failed = self._qa_failed(results)
                for cmd, proc in results:
                    print(f"$ {' '.join(cmd)}")
                    if proc.stdout:
                        print(proc.stdout.rstrip())
                    if proc.stderr:
                        print(proc.stderr.rstrip())

                repair_attempted = False
                repair_succeeded = False
                repair_owner = None
                repair_branch = None
                repair_attempts = 0

                if (
                    initial_failed
                    and auto_repair_qa
                    and allow_escalation
                    and decision.max_escalations > 0
                    and qa_repairs_used < max_qa_repair_cycles
                ):
                    qa_repairs_used += 1
                    repair_attempts = 1
                    repair_attempted = True

                    # QA routing decisions use fallback_owner as the preferred
                    # engineering repair owner when available.
                    preferred_owner = decision.fallback_owner or "codex"

                    self._agent_waiting(
                        "deterministic_qa",
                        project_name=plan.project_name,
                        task_id=decision.task_id,
                        phase="qa-repair",
                    )

                    repair = self._attempt_qa_repair(
                        root=root,
                        git=git,
                        integration_branch=integration_branch,
                        task_id=decision.task_id,
                        task_text=decision.task_text,
                        project_name=plan.project_name,
                        results=results,
                        attempt=qa_repairs_used,
                        primary_owner=preferred_owner,
                        allow_fallback=True,
                    )
                    repair_succeeded = bool(repair["success"])
                    repair_owner = repair["owner"]
                    repair_branch = repair["branch"]

                    if repair_succeeded:
                        print("â†’ Re-running deterministic QA after repair...")
                        git.create_or_switch_integration(integration_branch)

                        self._agent_start(
                            "deterministic_qa",
                            project_name=plan.project_name,
                            task_id=decision.task_id,
                            phase="qa-rerun",
                        )

                        try:
                            results = self._run_qa(
                                root,
                                decision.task_text,
                            )
                        except Exception:
                            self._agent_error(
                                "deterministic_qa",
                                project_name=plan.project_name,
                                task_id=decision.task_id,
                                phase="qa-rerun",
                            )
                            raise
                        for cmd, proc in results:
                            print(f"$ {' '.join(cmd)}")
                            if proc.stdout:
                                print(proc.stdout.rstrip())
                            if proc.stderr:
                                print(proc.stderr.rstrip())

                failed = self._qa_failed(results)
                qa_stdout, qa_stderr = self._qa_output(results)

                if failed:
                    self._agent_error(
                        "deterministic_qa",
                        project_name=plan.project_name,
                        task_id=decision.task_id,
                        phase="qa",
                    )
                else:
                    self._agent_idle(
                        "deterministic_qa",
                    )

                records.append(
                    ExecutionRecord(
                        task_id=decision.task_id,
                        owner=decision.primary_owner,
                        branch=integration_branch,
                        status="failed" if failed else "success",
                        command_preview="; ".join(" ".join(cmd) for cmd, _ in results),
                        return_code=1 if failed else 0,
                        stdout=qa_stdout,
                        stderr=qa_stderr,
                        initial_qa_failed=initial_failed,
                        repair_attempted=repair_attempted,
                        repair_attempts=repair_attempts,
                        repair_owner=repair_owner,
                        repair_branch=repair_branch,
                        repair_succeeded=repair_succeeded and not failed,
                        qa_profile=qa_profile,
                    )
                )

                # ERROR describes the result, not a permanently busy/broken agent.
                self._agent_idle("deterministic_qa")

                continue

            adapter = self.adapters.get(decision.primary_owner)
            if not adapter:
                records.append(
                    ExecutionRecord(
                        task_id=decision.task_id,
                        owner=decision.primary_owner,
                        branch=task_branch,
                        status="skipped",
                        stderr="Unsupported execution owner.",
                    )
                )
                continue

            if not adapter.available():
                records.append(
                    ExecutionRecord(
                        task_id=decision.task_id,
                        owner=decision.primary_owner,
                        branch=task_branch,
                        status="failed",
                        command_preview=self._command_preview(decision.primary_owner, prompt),
                        stderr=f"Required CLI binary '{adapter.binary}' is not available in PATH.",
                    )
                )
                continue

            # Every implementation task starts from latest cumulative integration state.
            git.create_or_reset_branch_from(task_branch, integration_branch)
            base_sha = git.head_sha()

            print(f"â†’ Starting {decision.primary_owner}...")

            self._agent_start(
                decision.primary_owner,
                project_name=plan.project_name,
                task_id=decision.task_id,
                phase="implementation",
            )

            try:
                proc = self._run_adapter(
                    adapter,
                    root,
                    prompt,
                    model=getattr(decision, "primary_model", None),
                    effort=getattr(decision, "primary_effort", None),
                )
            except Exception:
                self._agent_error(
                    decision.primary_owner,
                    project_name=plan.project_name,
                    task_id=decision.task_id,
                    phase="implementation",
                )
                raise

            self._record_usage(
                proc=proc,
                owner=decision.primary_owner,
                project_name=plan.project_name,
                task_id=decision.task_id,
                phase="implementation",
                requested_model=getattr(decision, "primary_model", None),
                requested_effort=getattr(decision, "primary_effort", None),
                goat_tier=getattr(decision, "goat_tier", None),
            )

            final_proc = proc
            escalated = False
            escalation_owner = None
            command_owner = decision.primary_owner

            # A zero CLI exit code is NOT enough. Implementation tasks must leave
            # actual repository changes that can be committed.
            primary_changed = proc.returncode == 0 and git.has_changes()
            primary_failed = proc.returncode != 0 or not primary_changed

            if primary_failed:
                fallback = (
                    decision.fallback_owner
                    if allow_escalation and decision.max_escalations > 0
                    else None
                )
                fallback_adapter = self.adapters.get(fallback) if fallback else None

                if fallback_adapter and fallback_adapter.available():
                    reason = (
                        f"return code {proc.returncode}"
                        if proc.returncode != 0
                        else "CLI returned success but produced no repository changes"
                    )
                    print(f"â†’ Primary failed ({reason}). Escalating once to {fallback}...")

                    # Remove partial/empty primary state before fallback.
                    self._agent_error(
                        decision.primary_owner,
                        project_name=plan.project_name,
                        task_id=decision.task_id,
                        phase="implementation",
                    )

                    git.reset_hard_to(integration_branch)
                    git.create_or_reset_branch_from(
                        task_branch,
                        integration_branch,
                    )

                    self._agent_start(
                        fallback,
                        project_name=plan.project_name,
                        task_id=decision.task_id,
                        phase="fallback",
                    )

                    try:
                        final_proc = self._run_adapter(
                            fallback_adapter,
                            root,
                            prompt,
                            model=getattr(decision, "fallback_model", None),
                            effort=getattr(decision, "fallback_effort", None),
                        )
                    except Exception:
                        self._agent_error(
                            fallback,
                            project_name=plan.project_name,
                            task_id=decision.task_id,
                            phase="fallback",
                        )
                        raise

                    self._record_usage(
                        proc=final_proc,
                        owner=fallback,
                        project_name=plan.project_name,
                        task_id=decision.task_id,
                        phase="fallback",
                        requested_model=getattr(decision, "fallback_model", None),
                        requested_effort=getattr(decision, "fallback_effort", None),
                        goat_tier="esc",
                    )

                    escalated = True
                    escalation_owner = fallback
                    command_owner = fallback

            implementation_changed = (
                final_proc.returncode == 0 and git.has_changes()
            )

            if implementation_changed:
                changed = git.commit_all(
                    f"{decision.task_id}: {decision.task_text}"
                )

                if not changed:
                    self._agent_error(
                        command_owner,
                        project_name=plan.project_name,
                        task_id=decision.task_id,
                        phase="implementation",
                    )

                    # Defensive: staged/working tree unexpectedly vanished.
                    git.reset_hard_to(integration_branch)
                    git.create_or_switch_integration(integration_branch)
                    records.append(
                        ExecutionRecord(
                            task_id=decision.task_id,
                            owner=decision.primary_owner,
                            branch=task_branch,
                            status="failed",
                            command_preview=self._command_preview(command_owner, prompt),
                            return_code=3,
                            stdout=final_proc.stdout,
                            stderr=(
                                (final_proc.stderr or "")
                                + "\nImplementation produced no committable repository changes."
                            ).strip(),
                            escalated=escalated,
                            escalation_owner=escalation_owner,
                        )
                    )
                    continue

                task_commit_sha = git.head_sha()
                if task_commit_sha == base_sha:
                    self._agent_error(
                        command_owner,
                        project_name=plan.project_name,
                        task_id=decision.task_id,
                        phase="implementation",
                    )

                    git.reset_hard_to(integration_branch)
                    git.create_or_switch_integration(integration_branch)
                    records.append(
                        ExecutionRecord(
                            task_id=decision.task_id,
                            owner=decision.primary_owner,
                            branch=task_branch,
                            status="failed",
                            command_preview=self._command_preview(command_owner, prompt),
                            return_code=4,
                            stdout=final_proc.stdout,
                            stderr="Git commit verification failed: task branch HEAD did not advance.",
                            escalated=escalated,
                            escalation_owner=escalation_owner,
                        )
                    )
                    continue

                # Merge task branch back to integration only after verified commit.
                git.create_or_switch_integration(integration_branch)
                git.merge_no_ff(
                    task_branch,
                    f"merge {decision.task_id}: {decision.task_text}",
                )

                integration_sha = git.head_sha()
                merged = (
                    integration_sha != base_sha
                    and git.is_ancestor(task_commit_sha, integration_branch)
                )

                if not merged:
                    self._agent_error(
                        command_owner,
                        project_name=plan.project_name,
                        task_id=decision.task_id,
                        phase="implementation",
                    )

                    records.append(
                        ExecutionRecord(
                            task_id=decision.task_id,
                            owner=decision.primary_owner,
                            branch=task_branch,
                            status="failed",
                            command_preview=self._command_preview(command_owner, prompt),
                            return_code=5,
                            stdout=final_proc.stdout,
                            stderr="Integration verification failed: task commit is not contained in integration branch.",
                            escalated=escalated,
                            escalation_owner=escalation_owner,
                        )
                    )
                    continue

                print(f"âœ“ {decision.task_id} committed and merged into {integration_branch}")

                self._agent_idle(
                    command_owner,
                )

                # If fallback succeeded, the failed primary owner must also
                # leave its transient ERROR state once the task is complete.
                if escalated and decision.primary_owner != command_owner:
                    self._agent_idle(decision.primary_owner)

                records.append(
                    ExecutionRecord(
                        task_id=decision.task_id,
                        owner=decision.primary_owner,
                        branch=task_branch,
                        status="success",
                        command_preview=self._command_preview(command_owner, prompt),
                        return_code=final_proc.returncode,
                        stdout=final_proc.stdout,
                        stderr=final_proc.stderr,
                        escalated=escalated,
                        escalation_owner=escalation_owner,
                    )
                )
            else:
                self._agent_error(
                    command_owner,
                    project_name=plan.project_name,
                    task_id=decision.task_id,
                    phase="implementation",
                )

                # Failed task, including false-success/no-change executions, is not merged.
                no_change = final_proc.returncode == 0 and not git.has_changes()
                git.reset_hard_to(integration_branch)
                git.create_or_switch_integration(integration_branch)

                reason = final_proc.stderr or ""
                if no_change:
                    reason = (
                        reason
                        + "\nCLI returned exit code 0 but produced no repository changes. "
                          "Task is treated as failed."
                    ).strip()

                records.append(
                    ExecutionRecord(
                        task_id=decision.task_id,
                        owner=decision.primary_owner,
                        branch=task_branch,
                        status="failed",
                        command_preview=self._command_preview(command_owner, prompt),
                        return_code=6 if no_change else final_proc.returncode,
                        stdout=final_proc.stdout,
                        stderr=reason,
                        escalated=escalated,
                        escalation_owner=escalation_owner,
                    )
                )

                # Failure remains in the execution report; live agents return idle.
                self._agent_idle(command_owner)
                if escalated and decision.primary_owner != command_owner:
                    self._agent_idle(decision.primary_owner)

        git.create_or_switch_integration(integration_branch) if not dry_run else None

        return ExecutionReport(
            project_name=plan.project_name,
            dry_run=dry_run,
            records=records,
        )
