import json
from pathlib import Path
from app.execution.models import ExecutionReport

class ExecutionStorage:
    def save(self, report: ExecutionReport, runtime_root: str | Path) -> Path:
        runtime_root = Path(runtime_root)
        project_dir = (
            runtime_root
            / "execution"
            / report.project_name
        )

        target = (
            project_dir
            / "execution_report.json"
        )

        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        payload = json.dumps(
            report.model_dump(),
            indent=2,
            ensure_ascii=False,
        )

        # Compatibility/latest pointer used by the existing
        # orchestration + delivery pipeline.
        target.write_text(
            payload,
            encoding="utf-8",
        )

        # Preserve immutable per-run report history.
        if report.run_id:
            run_target = (
                project_dir
                / "runs"
                / report.run_id
                / "execution_report.json"
            )

            run_target.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            run_target.write_text(
                payload,
                encoding="utf-8",
            )

        return target
