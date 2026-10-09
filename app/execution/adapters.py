import os
import shutil
import subprocess
import threading
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

        popen_kwargs = {
            "cwd": repo,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "bufsize": 1,
        }

        if os.name == "nt":
            popen_kwargs["creationflags"] = (
                subprocess.CREATE_NEW_PROCESS_GROUP
            )

        proc = subprocess.Popen(
            cmd,
            **popen_kwargs,
        )

        output = []
        assert proc.stdout is not None

        def read_output() -> None:
            try:
                for line in proc.stdout:
                    print(line, end="", flush=True)
                    output.append(line)
            except (ValueError, OSError):
                # The main thread may close the pipe while
                # terminating an interrupted/timed-out child.
                return

        reader = threading.Thread(
            target=read_output,
            name=f"adapter-output:{self.binary}",
            daemon=True,
        )
        reader.start()

        def stop_process() -> None:
            if proc.poll() is not None:
                return

            if os.name == "nt":
                try:
                    subprocess.run(
                        [
                            "taskkill",
                            "/PID",
                            str(proc.pid),
                            "/T",
                            "/F",
                        ],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=5.0,
                        check=False,
                    )
                except (
                    OSError,
                    subprocess.TimeoutExpired,
                ):
                    pass

                try:
                    proc.wait(timeout=2.0)
                    return
                except subprocess.TimeoutExpired:
                    pass

            try:
                proc.terminate()
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                if proc.poll() is None:
                    proc.kill()

                try:
                    proc.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    # Never hide the original timeout/interrupt.
                    pass
            except (OSError, ProcessLookupError):
                pass

        try:
            return_code = proc.wait(timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            stop_process()
            raise
        finally:
            if proc.poll() is not None:
                try:
                    proc.stdout.close()
                except (OSError, ValueError):
                    pass

            reader.join(timeout=2.0)

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
