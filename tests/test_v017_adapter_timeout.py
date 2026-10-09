import subprocess
import sys
import threading
import time

import pytest

from app.execution.adapters import BaseAdapter


class PythonAdapter(BaseAdapter):
    binary = "python-test"

    def __init__(self, source):
        self.source = source

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
        ]


def test_streaming_adapter_returns_output():
    adapter = PythonAdapter(
        "print('hello', flush=True)"
    )

    result = adapter.run(
        ".",
        "ignored",
        timeout=5,
        stream=True,
    )

    assert result.returncode == 0
    assert "hello" in result.stdout


def test_streaming_timeout_applies_while_stdout_is_silent():
    adapter = PythonAdapter(
        "import time; time.sleep(10)"
    )

    started = time.monotonic()

    with pytest.raises(subprocess.TimeoutExpired):
        adapter.run(
            ".",
            "ignored",
            timeout=0.2,
            stream=True,
        )

    elapsed = time.monotonic() - started

    assert elapsed < 4.0


def test_streaming_timeout_preserves_output_before_timeout():
    adapter = PythonAdapter(
        (
            "import time; "
            "print('before-timeout', flush=True); "
            "time.sleep(10)"
        )
    )

    with pytest.raises(subprocess.TimeoutExpired):
        adapter.run(
            ".",
            "ignored",
            timeout=0.2,
            stream=True,
        )


def test_streaming_reader_thread_stops_after_success():
    adapter = PythonAdapter(
        "print('done', flush=True)"
    )

    adapter.run(
        ".",
        "ignored",
        timeout=5,
        stream=True,
    )

    leaked = [
        thread.name
        for thread in threading.enumerate()
        if thread.name == "adapter-output:python-test"
    ]

    assert leaked == []


def test_non_stream_mode_keeps_existing_timeout_contract():
    adapter = PythonAdapter(
        "import time; time.sleep(10)"
    )

    with pytest.raises(subprocess.TimeoutExpired):
        adapter.run(
            ".",
            "ignored",
            timeout=0.2,
            stream=False,
        )
