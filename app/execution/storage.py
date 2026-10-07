import json
from pathlib import Path
from app.execution.models import ExecutionReport

class ExecutionStorage:
    def save(self, report: ExecutionReport, runtime_root: str | Path) -> Path:
        runtime_root = Path(runtime_root)
        target = runtime_root / "execution" / report.project_name / "execution_report.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(report.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return target
