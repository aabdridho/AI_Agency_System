from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import uuid4
from typing import Any

from app.delivery.checker import DeliveryChecker
from app.delivery.engine import DeliveryEngine
from app.delivery.resolver import (
    InternalResolutionError,
    InternalResolver,
)
from app.discovery.confirmation import ConfirmationGate
from app.discovery.engine import RequirementDiscoveryEngine
from app.documentation.generator import ProjectDocumentationGenerator
from app.execution.billing import (
    BillingConfig,
    write_project_billing_summary,
)
from app.execution.costs import write_project_cost_summary
from app.execution.engine import ExecutionEngine
from app.execution.savings import write_project_savings_summary
from app.execution.storage import ExecutionStorage
from app.execution.usage import UsageLedger
from app.execution.events import ExecutionEventLedger
from app.orchestration.models import OrchestrationState
from app.orchestration.state import OrchestrationStateStore
from app.routing.engine import RoutingEngine
from app.routing.storage import RoutingStorage
from app.workspace import OUTPUT_ROOT, SYSTEM_ROOT


STAGES = (
    "discovery",
    "documentation",
    "routing",
    "execution",
    "delivery",
    "economics",
    "deployment",
)


def _delivery_allows_auto_resolution(checks) -> bool:
    """Auto-resolve only when no higher-priority blocker exists."""
    blocker_classes = {
        check.blocker_class
        for check in checks
        if check.status == "blocker"
    }

    has_auto = any(
        check.status == "blocker"
        and check.blocker_class == "AUTO_RESOLVABLE_INTERNAL"
        and check.auto_resolvable
        for check in checks
    )

    return (
        has_auto
        and "HARD_TECHNICAL_BLOCKER" not in blocker_classes
        and "CLIENT_INPUT_REQUIRED" not in blocker_classes
    )


def _read_json(
    path: Path,
) -> dict[str, Any] | None:
    if not path.is_file():
        return None

    try:
        return json.loads(
            path.read_text(
                encoding="utf-8-sig"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return None


class ProjectOrchestrator:
    """
    V0.14 orchestration state / resume foundation.

    Stage 1 responsibility:
    - inspect canonical project/runtime artifacts
    - reconstruct the current pipeline position
    - persist orchestration state
    - determine the next safe stage

    It intentionally does not execute model/deployment
    operations yet. Stage runners are added separately.
    """

    def __init__(
        self,
        runtime_root: str | Path | None = None,
        output_root: str | Path | None = None,
    ):
        self.runtime_root = Path(
            runtime_root
            if runtime_root is not None
            else SYSTEM_ROOT / "runtime_data"
        )

        self.output_root = Path(
            output_root
            if output_root is not None
            else OUTPUT_ROOT
        )

        self.state_store = (
            OrchestrationStateStore(
                self.runtime_root
            )
        )

    def project_root(
        self,
        project_name: str,
    ) -> Path:
        return (
            self.output_root
            / project_name
        )

    def _runtime_artifact(
        self,
        area: str,
        project_name: str,
        filename: str,
    ) -> Path:
        return (
            self.runtime_root
            / area
            / project_name
            / filename
        )

    def _completed_prefix(
        self,
        completed: set[str],
    ) -> list[str]:
        result = []

        for stage in STAGES:
            if stage not in completed:
                break

            result.append(stage)

        return result

    def inspect(
        self,
        project_name: str,
        *,
        persist: bool = True,
    ) -> OrchestrationState:
        project = self.project_root(
            project_name
        )

        completed: set[str] = set()

        # ----------------------------------------------------
        # Discovery / documentation
        # ----------------------------------------------------

        docs = project / "docs"

        requirement_file = (
            docs / "requirement.md"
        )

        requirement_approved = False

        if requirement_file.is_file():
            try:
                requirement_approved = (
                    DeliveryChecker(
                        project
                    )
                    .approved_requirement_gate()
                    .status
                    == "pass"
                )
            except Exception:
                requirement_approved = False

        if requirement_approved:
            completed.add("discovery")

        if (
            requirement_approved
            and (docs / "task.md").is_file()
        ):
            completed.add("documentation")

        # ----------------------------------------------------
        # Routing
        # ----------------------------------------------------

        routing = _read_json(
            self._runtime_artifact(
                "routing",
                project_name,
                "routing_plan.json",
            )
        )

        if routing:
            completed.add("routing")

        # ----------------------------------------------------
        # Execution
        # ----------------------------------------------------

        execution = _read_json(
            self._runtime_artifact(
                "execution",
                project_name,
                "execution_report.json",
            )
        )

        execution_failed = False
        execution_dry_run = False

        if execution:
            records = execution.get(
                "records",
                [],
            )

            execution_failed = any(
                r.get("status") == "failed"
                for r in records
            )

            execution_dry_run = bool(
                execution.get("dry_run")
            )

            if (
                not execution_failed
                and not execution_dry_run
            ):
                completed.add(
                    "execution"
                )

        # ----------------------------------------------------
        # Delivery
        # ----------------------------------------------------

        delivery = _read_json(
            self._runtime_artifact(
                "delivery",
                project_name,
                "delivery_report.json",
            )
        )

        delivery_status = None
        client_input_required = False
        hard_technical_blocker = False

        if delivery:
            delivery_status = delivery.get(
                "overall_status"
            )

            blockers = delivery.get(
                "blocker_summary",
                {},
            )

            client_input_required = (
                blockers.get(
                    "CLIENT_INPUT_REQUIRED",
                    0,
                )
                > 0
            )

            hard_technical_blocker = (
                blockers.get(
                    "HARD_TECHNICAL_BLOCKER",
                    0,
                )
                > 0
            )

            if delivery_status in {
                "ready",
                "warning",
            }:
                completed.add(
                    "delivery"
                )

        # ----------------------------------------------------
        # Economics
        # ----------------------------------------------------

        usage_dir = (
            self.runtime_root
            / "usage"
            / project_name
        )

        economics_files = (
            "cost_summary.json",
            "savings_summary.json",
            "billing_summary.json",
        )

        economics_done = all(
            (usage_dir / filename).is_file()
            for filename in economics_files
        )

        if economics_done:
            completed.add("economics")

        # ----------------------------------------------------
        # Deployment
        # ----------------------------------------------------

        deployment_result = _read_json(
            self._runtime_artifact(
                "deployment",
                project_name,
                "deployment_result.json",
            )
        )

        if (
            deployment_result
            and deployment_result.get(
                "status"
            )
            == "deployed"
        ):
            completed.add("deployment")

        completed_stages = (
            self._completed_prefix(
                completed
            )
        )

        # ----------------------------------------------------
        # State classification
        # ----------------------------------------------------

        if "deployment" in completed_stages:
            state = OrchestrationState(
                project_name=project_name,
                status="completed",
                current_stage=None,
                completed_stages=completed_stages,
            )

        elif execution_failed:
            state = OrchestrationState(
                project_name=project_name,
                status="failed",
                current_stage="execution",
                completed_stages=completed_stages,
                failed_stage="execution",
                last_error=(
                    "Execution report contains "
                    "one or more failed tasks."
                ),
            )

        elif hard_technical_blocker:
            state = OrchestrationState(
                project_name=project_name,
                status="failed",
                current_stage="delivery",
                completed_stages=completed_stages,
                failed_stage="delivery",
                last_error=(
                    "Delivery readiness contains "
                    "one or more hard technical blockers."
                ),
            )

        elif client_input_required:
            state = OrchestrationState(
                project_name=project_name,
                status="waiting_input",
                current_stage="delivery",
                completed_stages=completed_stages,
                waiting_for="client_input",
            )

        elif (
            delivery
            and delivery_status == "blocked"
        ):
            state = OrchestrationState(
                project_name=project_name,
                status="failed",
                current_stage="delivery",
                completed_stages=completed_stages,
                failed_stage="delivery",
                last_error=(
                    "Delivery readiness contains "
                    "blocking checks."
                ),
            )

        elif "economics" in completed_stages:
            state = OrchestrationState(
                project_name=project_name,
                status="waiting_approval",
                current_stage="deployment",
                completed_stages=completed_stages,
                waiting_for="deployment_approval",
            )

        elif "delivery" in completed_stages:
            state = OrchestrationState(
                project_name=project_name,
                status="idle",
                current_stage="economics",
                completed_stages=completed_stages,
            )

        elif "execution" in completed_stages:
            state = OrchestrationState(
                project_name=project_name,
                status="idle",
                current_stage="delivery",
                completed_stages=completed_stages,
            )

        elif execution_dry_run:
            state = OrchestrationState(
                project_name=project_name,
                status="waiting_approval",
                current_stage="execution",
                completed_stages=completed_stages,
                waiting_for="real_execution_approval",
            )

        elif "routing" in completed_stages:
            state = OrchestrationState(
                project_name=project_name,
                status="waiting_approval",
                current_stage="execution",
                completed_stages=completed_stages,
                waiting_for="real_execution_approval",
            )

        elif "documentation" in completed_stages:
            state = OrchestrationState(
                project_name=project_name,
                status="idle",
                current_stage="routing",
                completed_stages=completed_stages,
            )

        elif "discovery" in completed_stages:
            state = OrchestrationState(
                project_name=project_name,
                status="idle",
                current_stage="documentation",
                completed_stages=completed_stages,
            )

        else:
            state = OrchestrationState(
                project_name=project_name,
                status="waiting_input",
                current_stage="discovery",
                completed_stages=[],
                waiting_for="client_brief",
            )

        if persist:
            self.state_store.save(
                state
            )

            # Return the persisted representation,
            # including updated_at.
            persisted = (
                self.state_store.load(
                    project_name
                )
            )

            if persisted is not None:
                return persisted

        return state

    def resume(
        self,
        project_name: str,
    ) -> OrchestrationState:
        """
        Resume is artifact-driven.

        Persisted state is useful telemetry, but artifacts
        remain authoritative so stale state cannot force a
        completed stage to execute again.
        """
        return self.inspect(
            project_name,
            persist=True,
        )

    def analyze_brief(
        self,
        brief: str,
        references: list[str] | None = None,
    ):
        if not brief.strip():
            raise ValueError(
                "Client brief wajib diisi."
            )

        return RequirementDiscoveryEngine().analyze(
            brief.strip(),
            references or [],
        )

    def approve_discovery(
        self,
        result,
    ):
        approved = ConfirmationGate().approve_final(
            result
        )

        if (
            not approved.client_approved
            or not approved.ready_for_development
        ):
            raise ValueError(
                "Requirement belum memenuhi final approval gate."
            )

        return approved

    def generate_documentation(
        self,
        project_name: str,
        result,
    ) -> list[Path]:
        root = self.project_root(
            project_name
        )

        if root.exists():
            docs = root / "docs"

            if any(
                (
                    docs / name
                ).exists()
                for name in (
                    "requirement.md",
                    "task.md",
                    "architecture.md",
                )
            ):
                raise FileExistsError(
                    "Project sudah memiliki baseline documentation. "
                    "Orchestrator tidak akan menimpa secara diam-diam."
                )

        generated = (
            ProjectDocumentationGenerator()
            .generate(
                result,
                root,
            )
        )

        self.resume(
            project_name
        )

        return generated

    def _require_project(
        self,
        project_name: str,
    ) -> Path:
        root = self.project_root(
            project_name
        )

        if not root.is_dir():
            raise FileNotFoundError(
                f"Project workspace tidak ditemukan: {root}"
            )

        return root

    def run_routing(
        self,
        project_name: str,
    ) -> OrchestrationState:
        root = self._require_project(
            project_name
        )

        plan = RoutingEngine().build_plan(
            root
        )

        RoutingStorage().save(
            plan,
            self.runtime_root,
        )

        return self.resume(
            project_name
        )

    def execution_preflight(
        self,
        project_name: str,
    ) -> list[str]:
        root = self._require_project(
            project_name
        )

        plan = RoutingEngine().build_plan(
            root
        )

        engine = ExecutionEngine()

        missing = [
            binary
            for binary in sorted(
                engine.required_binaries(plan)
            )
            if shutil.which(binary) is None
        ]

        return missing

    def run_execution(
        self,
        project_name: str,
    ) -> OrchestrationState:
        root = self._require_project(
            project_name
        )

        plan = RoutingEngine().build_plan(
            root
        )

        missing = self.execution_preflight(
            project_name
        )

        if missing:
            raise RuntimeError(
                "CLI required untuk real execution "
                "tidak tersedia di PATH: "
                + ", ".join(missing)
            )

        run_id = uuid4().hex

        usage_ledger = UsageLedger(
            self.runtime_root
            / "usage"
        )

        event_ledger = ExecutionEventLedger(
            self.runtime_root
            / "execution"
        )

        report = ExecutionEngine(
            usage_ledger=usage_ledger,
            event_ledger=event_ledger,
            run_id=run_id,
        ).execute(
            plan,
            root,
            dry_run=False,
            allow_escalation=True,
        )

        ExecutionStorage().save(
            report,
            self.runtime_root,
        )

        return self.resume(
            project_name
        )

    def run_delivery(
        self,
        project_name: str,
    ) -> OrchestrationState:
        root = self._require_project(
            project_name
        )

        execution_report = (
            self.runtime_root
            / "execution"
            / project_name
            / "execution_report.json"
        )

        output_root = (
            self.runtime_root
            / "delivery"
        )

        engine = DeliveryEngine()

        report = engine.run(
            project_name=project_name,
            project_root=root,
            output_root=output_root,
            run_production_validation=True,
            source_execution_report=(
                str(execution_report)
                if execution_report.is_file()
                else None
            ),
        )

        hard_blockers = [
            check
            for check in report.checks
            if (
                check.status == "blocker"
                and check.blocker_class
                == "HARD_TECHNICAL_BLOCKER"
            )
        ]

        auto_blockers = [
            check
            for check in report.checks
            if (
                check.status == "blocker"
                and check.blocker_class
                == "AUTO_RESOLVABLE_INTERNAL"
                and check.auto_resolvable
            )
        ]

        if _delivery_allows_auto_resolution(report.checks):
            resolver = InternalResolver(root)

            try:
                resolver.resolve_deployment_target_to_vercel()
            except InternalResolutionError as exc:
                raise RuntimeError(
                    "Safe internal delivery resolution gagal: "
                    f"{exc}"
                ) from exc

            # Re-run readiness after the internal decision
            # has been safely committed.
            engine.run(
                project_name=project_name,
                project_root=root,
                output_root=output_root,
                run_production_validation=True,
                source_execution_report=(
                    str(execution_report)
                    if execution_report.is_file()
                    else None
                ),
            )

        return self.resume(
            project_name
        )

    def run_economics(
        self,
        project_name: str,
    ) -> OrchestrationState:
        usage_root = (
            self.runtime_root
            / "usage"
        )

        usage_file = (
            usage_root
            / project_name
            / "usage.jsonl"
        )

        if not usage_file.is_file():
            raise FileNotFoundError(
                "Usage ledger belum tersedia: "
                f"{usage_file}"
            )

        write_project_cost_summary(
            usage_root,
            project_name,
        )

        write_project_savings_summary(
            usage_root,
            project_name,
        )

        policy = BillingConfig(
            self.runtime_root
            / "config"
            / "billing.json"
        ).load()

        write_project_billing_summary(
            usage_root,
            project_name,
            policy=policy,
        )

        return self.resume(
            project_name
        )

    def run_until_blocked(
        self,
        project_name: str,
        *,
        approve_real_execution: bool = False,
    ) -> OrchestrationState:
        """
        Continue every safe automatic stage until the pipeline
        reaches input/approval/failure/completion.

        Production deployment is intentionally NOT executed here.
        """

        while True:
            state = self.resume(
                project_name
            )

            if state.status in {
                "failed",
                "completed",
            }:
                return state

            if state.status == "waiting_input":
                return state

            if (
                state.status == "waiting_approval"
                and state.waiting_for
                == "deployment_approval"
            ):
                return state

            if (
                state.status == "waiting_approval"
                and state.waiting_for
                == "real_execution_approval"
            ):
                if not approve_real_execution:
                    return state

                state = self.run_execution(
                    project_name
                )

                if state.status == "failed":
                    return state

                continue

            if state.current_stage == "routing":
                self.run_routing(
                    project_name
                )
                continue

            if state.current_stage == "delivery":
                self.run_delivery(
                    project_name
                )
                continue

            if state.current_stage == "economics":
                self.run_economics(
                    project_name
                )
                continue

            # Discovery and documentation are not automated yet.
            return state

    def next_stage(
        self,
        project_name: str,
    ) -> str | None:
        state = self.resume(
            project_name
        )

        return state.current_stage
