import contextlib
import functools
import inspect
import platform
import shutil
import socket
import subprocess
import sys
import threading
import time

import httpx
import pytest
import redis


@contextlib.contextmanager
def background_subprocess(*args, stdout=sys.stdout, stderr=sys.stdout, **kwargs):
    process = subprocess.Popen(*args, stdout=stdout, stderr=stderr, **kwargs)
    try:
        yield process
    finally:
        process.kill()
        process.communicate()


def timeout_after(seconds=30, *, message=None):
    timeout = f"Timeout after {seconds:.1f} seconds"
    message = timeout if message is None else f"{timeout}: {message}"

    def decorator(fn):
        if is_debugging():
            return fn

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            result = TimeoutError(message)

            def target():
                nonlocal result
                try:
                    result = fn(*args, **kwargs)
                except Exception as exc:
                    result = exc

            thread = threading.Thread(target=target)
            thread.daemon = True

            thread.start()
            thread.join(seconds)

            if isinstance(result, Exception):
                raise result

            return result

        return wrapper

    return decorator


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
def redis_server(scheme="redis://"):
    if platform.system() == "Windows":
        raise RuntimeError("redis-server is not available for Windows.")

    port = get_available_port()
    url = f"{scheme}127.0.0.1:{port}"
    redis_server_executable = shutil.which("redis-server")
    if redis_server_executable is None:
        raise RuntimeError("Unable to find redis-server executable")

    with background_subprocess([redis_server_executable, "--port", str(port)]):
        connection = redis.Redis.from_url(url)

        @timeout_after(message=f"Unable to establish connection to {url}")
        def wait_for_redis_server(poll=0.1):
            while True:
                with contextlib.suppress(redis.ConnectionError):
                    if connection.ping():
                        return url

                time.sleep(poll)

        yield wait_for_redis_server()


skip_redis_on_windows = pytest.mark.skipif(
    platform.system() == "Windows",
    reason="redis-server is not available for Windows.",
)


@contextlib.contextmanager
def ragna_worker(config):
    config_path = config.local_cache_root / "ragna.toml"
    if not config_path.exists():
        config.to_file(config_path)

    with background_subprocess(
        [sys.executable, "-m", "ragna", "worker", "--config", str(config_path)]
    ):

        @timeout_after(message="Unable to start worker")
        def wait_for_worker():
            # This seems quite brittle, but I didn't find a better way to check
            # whether the worker is ready. We are checking the logged messages until
            # we see the "ready" message.
            for line in sys.stderr:
                if "Huey consumer started" in line:
                    return

        yield wait_for_worker()


@contextlib.contextmanager
def ragna_api(config, *, start_worker=None):
    config_path = config.local_cache_root / "ragna.toml"
    if not config_path.exists():
        config.to_file(config_path)

    cmd = [sys.executable, "-m", "ragna", "api", "--config", str(config_path)]

    if start_worker is not None:
        cmd.append(f"--{'' if start_worker else 'no-'}start-worker")

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
