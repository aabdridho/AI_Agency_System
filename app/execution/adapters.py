import shutil
import subprocess
from pathlib import Path


class BaseAdapter:
    binary: str

    def available(self) -> bool:
        return shutil.which(self.binary) is not None

    def build_command(
        self,
        prompt: str,
        *,
        model: str | None = None,
        effort: str | None = None,
    ) -> list[str]:
        raise NotImplementedError

    def run(
        self,
        repo: str | Path,
        prompt: str,
        timeout: int = 1800,
        stream: bool = True,
        *,
        model: str | None = None,
        effort: str | None = None,
    ):
        cmd = self.build_command(
            prompt,
            model=model,
            effort=effort,
        )

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

    def build_command(
        self,
        prompt: str,
        *,
        model: str | None = None,
        effort: str | None = None,
    ) -> list[str]:
        cmd = [
            "claude",
            "-p",
            "--permission-mode",
            "acceptEdits",
            "--permission-prompts",
            "none",
            "--output-format",
            "json",
        ]

        if model:
            cmd += ["--model", model]

        if effort:
            cmd += ["--effort", effort]

        cmd.append(prompt)
        return cmd


class CodexAdapter(BaseAdapter):
    binary = "codex"

    def build_command(
        self,
        prompt: str,
        *,
        model: str | None = None,
        effort: str | None = None,
    ) -> list[str]:
        cmd = [
            "codex",
            "exec",
            "--approve-for-me",
            "--json",
        ]

        if model:
            cmd += ["--model", model]

        # Codex CLI 0.160.1 does not expose a documented --effort flag in
        # the audited CLI contract, so effort is recorded as routing
        # metadata but is intentionally not forwarded yet.

        cmd.append(prompt)
        return cmd
