import contextlib
import inspect
import socket
import subprocess
import sys
import time

import httpx

from ragna._utils import timeout_after


@contextlib.contextmanager
def background_subprocess(*args, stdout=sys.stdout, stderr=sys.stdout, **kwargs):
    process = subprocess.Popen(*args, stdout=stdout, stderr=stderr, **kwargs)
    try:
        yield process
    finally:
        process.kill()
        process.communicate()


# Vendored from pytest-timeout
# https://github.com/pytest-dev/pytest-timeout/blob/d91e6d8d69ad706e38a2c9de461a72c4d19777ff/pytest_timeout.py#L218-L247
def is_debugging():
    trace_func = sys.gettrace()
    trace_module = None
    if trace_func:
        trace_module = inspect.getmodule(trace_func) or inspect.getmodule(
            trace_func.__class__
        )
    if trace_module:
        parts = trace_module.__name__.split(".")
        for name in {"pydevd", "bdb", "pydevd_frame_evaluator"}:
            if any(part.startswith(name) for part in parts):
                return True
    return False


def get_available_port():
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def ragna_api(config):
    config_path = config.local_cache_root / "ragna.toml"
    if not config_path.exists():
        config.to_file(config_path)

    cmd = [sys.executable, "-m", "ragna", "api", "--config", str(config_path)]

    with background_subprocess(cmd):

        @timeout_after(message="Unable to start ragna api")
        def wait_for_ragna_api(poll=0.1):
            url = config.api.url
            while True:
                with contextlib.suppress(httpx.ConnectError):
                    response = httpx.get(url)
                    if response.is_success:
                        return url

                time.sleep(poll)

        yield wait_for_ragna_api()
