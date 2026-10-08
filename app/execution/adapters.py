import shutil
import subprocess
from pathlib import Path


class BaseAdapter:
    binary: str

    def available(self) -> bool:
        return shutil.which(self.binary) is not None

    def build_command(self, prompt: str) -> list[str]:
        raise NotImplementedError

    def run(self, repo: str | Path, prompt: str, timeout: int = 1800, stream: bool = True):
        cmd = self.build_command(prompt)

        if not stream:
            return subprocess.run(
                cmd,
                cwd=repo,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )

        proc = subprocess.Popen(
            cmd,
            cwd=repo,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

        output = []
        assert proc.stdout is not None
        for line in proc.stdout:
            print(line, end="", flush=True)
            output.append(line)

        return_code = proc.wait(timeout=timeout)

        class Result:
            pass

        result = Result()
        result.returncode = return_code
        result.stdout = "".join(output)
        result.stderr = ""
        return result


class ClaudeCodeAdapter(BaseAdapter):
    binary = "claude"

    def build_command(self, prompt: str) -> list[str]:
        # Non-interactive execution that allows repository edits while still
        # keeping Claude inside its normal permission model.
        return [
            "claude",
            "-p",
            "--permission-mode",
            "acceptEdits",
            "--permission-prompts",
            "none",
            "--output-format",
            "json",
            prompt,
        ]


class CodexAdapter(BaseAdapter):
    binary = "codex"

    def build_command(self, prompt: str) -> list[str]:
        # Codex exec defaults can be read-only. Explicitly grant write access
        # to the current workspace while keeping approval non-interactive.
        return [
            "codex",
            "exec",
            "--approve-for-me",
            "--json",
            prompt,
        ]
