import re
from pathlib import Path

TASK_RE = re.compile(r"^\s*-\s*\[\s*[ xX]?\s*\]\s*(.+?)\s*$")

class TaskParser:
    def parse_markdown(self, path: str | Path) -> list[str]:
        path = Path(path)
        tasks = []
        for raw in path.read_text(encoding="utf-8").splitlines():
            m = TASK_RE.match(raw)
            if m:
                text = m.group(1).strip()
                if text:
                    tasks.append(text)
        return tasks
