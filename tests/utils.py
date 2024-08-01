import contextlib
import platform
import socket
import subprocess
import sys

import pytest

skip_on_windows = pytest.mark.skipif(
    platform.system() == "Windows", reason="Test is broken skipped on Windows"
)


@contextlib.contextmanager
def background_subprocess(*args, stdout=sys.stdout, stderr=sys.stdout, **kwargs):
    process = subprocess.Popen(args, stdout=stdout, stderr=stderr, **kwargs)
    try:
        yield process
    finally:
        process.kill()
        process.communicate()


def get_available_port():
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]
