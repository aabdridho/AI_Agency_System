from __future__ import annotations

from collections import Counter
from pathlib import Path

from .checker import DeliveryChecker
from .client_input import ClientInputPacketGenerator
from .models import DeliveryReport


class DeliveryEngine:
    def run(
        self,
        *,
        project_name,
        project_root,
        output_root,
        run_production_validation=True,
        source_execution_report=None,
    ):
        repo = Path(project_root)
        checker = DeliveryChecker(repo)
        checks = checker.all_static_checks()
        commands = []

        if run_production_validation:
            validation_check, commands = checker.run_production_validation()
            checks.append(validation_check)

        if any(c.status == "blocker" for c in checks):
            overall = "blocked"
        elif any(c.status == "warning" for c in checks):
            overall = "warning"
        else:
            overall = "ready"

        summary = Counter(
            c.blocker_class
            for c in checks
            if c.status == "blocker" and c.blocker_class
        )

        out_dir = Path(output_root) / project_name
        out_dir.mkdir(parents=True, exist_ok=True)

        client_packet = ClientInputPacketGenerator(repo).render_markdown(
            project_name=project_name,
            checks=checks,
        )
        client_packet_path = None
        packet_file = out_dir / "client_input_request.md"

        if client_packet:
            packet_file.write_text(client_packet, encoding="utf-8")
            client_packet_path = str(packet_file)
        elif packet_file.exists():
            # Avoid stale request packets after client blockers are resolved.
            packet_file.unlink()

        report = DeliveryReport(
            project_name=project_name,
            project_root=str(repo),
            overall_status=overall,
            checks=checks,
            production_commands=commands,
            source_execution_report=source_execution_report,
            blocker_summary=dict(summary),
            client_input_request=client_packet_path,
        )

        (out_dir / "delivery_report.json").write_text(
            report.model_dump_json(indent=2),
            encoding="utf-8",
        )

        lines = [
            f"# Delivery Readiness - {project_name}",
            "",
            f"Overall status: **{overall.upper()}**",
            "",
        ]

        if summary:
            lines += ["## Blocker Ownership", ""]
            for key in (
                "AUTO_RESOLVABLE_INTERNAL",
                "CLIENT_INPUT_REQUIRED",
                "HARD_TECHNICAL_BLOCKER",
            ):
                lines.append(f"- **{key}**: {summary.get(key, 0)}")
            lines.append("")

        lines += ["## Checks", ""]
        for check in checks:
            label = {
                "pass": "PASS",
                "warning": "WARN",
                "blocker": "BLOCK",
            }[check.status]
            suffix = f" [{check.blocker_class}]" if check.blocker_class else ""
            lines.append(
                f"- **[{label}] {check.title}**{suffix} — {check.detail}"
            )
            if check.proposed_resolution:
                lines.append(
                    f"  - Proposed resolution: {check.proposed_resolution}"
                )
            if check.remediation:
                lines.append(f"  - Remediation: {check.remediation}")

        if client_packet_path:
            lines += [
                "",
                "## Client Input Request",
                "",
                f"- Generated: `{client_packet_path}`",
            ]

        if commands:
            lines += ["", "## Production Validation Commands", ""]
            lines += [f"- `{cmd}`" for cmd in commands]

        (out_dir / "delivery_report.md").write_text(
            "\n".join(lines) + "\n",
            encoding="utf-8",
        )

        return report
