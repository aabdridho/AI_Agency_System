from pathlib import Path
from app.routing.task_parser import TaskParser
from app.routing.classifier import TaskClassifier
from app.routing.policy import RoutingPolicy
from app.routing.models import RoutingPlan

class RoutingEngine:
    def __init__(self, policy: RoutingPolicy | None = None):
        self.parser = TaskParser()
        self.classifier = TaskClassifier()
        self.policy = policy or RoutingPolicy()

    def build_plan(self, project_root: str | Path) -> RoutingPlan:
        project_root = Path(project_root)
        task_file = project_root / "docs" / "task.md"

        if not task_file.exists():
            raise FileNotFoundError(f"task.md not found: {task_file}")

        tasks = self.parser.parse_markdown(task_file)
        if not tasks:
            raise ValueError("No checkbox tasks found in task.md")

        decisions = []
        for index, task in enumerate(tasks, start=1):
            category, confidence = self.classifier.classify(task)
            decisions.append(
                self.policy.decide(
                    task_id=f"TASK-{index:03d}",
                    task_text=task,
                    category=category,
                    confidence=confidence,
                )
            )

        return RoutingPlan(
            project_name=project_root.name,
            source_task_file=str(task_file),
            decisions=decisions,
        )
