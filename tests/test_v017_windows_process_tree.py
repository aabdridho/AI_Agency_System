import os
import subprocess
import sys
import time

import pytest

from app.execution.adapters import BaseAdapter


class _TreeAdapter(BaseAdapter):
    binary = "python-tree-test"

    def __init__(self, source, pid_file):
        self.source = source
        self.pid_file = pid_file

    def build_command(
        self,
        prompt,
        *,
        model=None,
        effort=None,
    ):
        return [
            sys.executable,
            "-c",
            self.source,
            str(self.pid_file),
        ]


def _pid_is_running_windows(pid):
    result = subprocess.run(
        [
            "tasklist",
            "/FI",
            f"PID eq {pid}",
            "/FO",
            "CSV",
            "/NH",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    output = result.stdout or ""

    return f'"{pid}"' in output


@pytest.mark.skipif(
    os.name != "nt",
    reason="Windows process-tree contract",
)
def test_streaming_timeout_kills_descendant_process(
    tmp_path,
):
    pid_file = tmp_path / "child.pid"

    source = (
        "import subprocess,sys,time,pathlib; "
        "child=subprocess.Popen(["
        "sys.executable,'-c','import time; time.sleep(30)']); "
        "pathlib.Path(sys.argv[1]).write_text("
        "str(child.pid),encoding='utf-8'); "
        "time.sleep(30)"
    )

    adapter = _TreeAdapter(
        source,
        pid_file,
    )

    with pytest.raises(subprocess.TimeoutExpired):
        adapter.run(
            ".",
            "ignored",
            timeout=0.5,
            stream=True,
        )

    deadline = time.monotonic() + 2.0

    while (
        not pid_file.exists()
        and time.monotonic() < deadline
    ):
        time.sleep(0.02)

    assert pid_file.exists()

    child_pid = int(
        pid_file.read_text(
            encoding="utf-8"
        ).strip()
    )

    deadline = time.monotonic() + 3.0

    while (
        _pid_is_running_windows(child_pid)
        and time.monotonic() < deadline
    ):
        time.sleep(0.05)

    assert not _pid_is_running_windows(child_pid)


@pytest.mark.skipif(
    os.name != "nt",
    reason="Windows process-group contract",
)
def test_streaming_adapter_uses_new_process_group(
    monkeypatch,
):
    observed = {}

    class FakeStdout:
        def __iter__(self):
            return iter([])

        def close(self):
            pass

    class FakeProcess:
        pid = 12345
        stdout = FakeStdout()

        def poll(self):
            return 0

        def wait(self, timeout=None):
            return 0

    def fake_popen(cmd, **kwargs):
        observed.update(kwargs)
        return FakeProcess()

    monkeypatch.setattr(
        subprocess,
        "Popen",
        fake_popen,
    )

    class Adapter(BaseAdapter):
        binary = "fake"

        def build_command(
            self,
            prompt,
            *,
            model=None,
            effort=None,
        ):
            return ["fake"]

    result = Adapter().run(
        ".",
        "ignored",
        timeout=1,
        stream=True,
    )

    assert result.returncode == 0

    assert (
        observed["creationflags"]
        & subprocess.CREATE_NEW_PROCESS_GROUP
    )
