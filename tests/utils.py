import platform
import socket

import pytest

skip_on_windows = pytest.mark.skipif(
    platform.system() == "Windows", reason="Test is broken skipped on Windows"
)


def get_available_port():
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]
