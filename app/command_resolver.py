import shutil
import sys


def resolve_node_cli(name: str) -> str | None:
    """Resolve a Node CLI deterministically for the current platform."""
    candidates = (
        [f"{name}.cmd", name]
        if sys.platform == "win32"
        else [name]
    )

    for candidate in candidates:
        if shutil.which(candidate):
            return candidate

    return None
