import contextlib
import functools
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
def background_subprocess(
    *args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs
):
    process = subprocess.Popen(*args, stdout=stdout, stderr=stderr, **kwargs)
    try:
        yield process
    finally:
        process.kill()
        stdout, stderr = process.communicate()
        if stdout:
            sys.stdout.buffer.write(stdout)
            sys.stdout.flush()
        if stderr:
            sys.stderr.buffer.write(stderr)
            sys.stderr.flush()


def timeout_after(seconds=5, *, message=None):
    timeout = f"Timeout after {seconds:.1f} seconds"
    message = timeout if message is None else f"{timeout}: {message}"

    def decorator(fn):
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
    ) as process:

        @timeout_after(message="Unable to start worker")
        def wait_for_worker():
            # This seems quite brittle, but I didn't find a better way to check
            # whether the worker is ready. We are checking the logged messages until
            # we see the "ready" message.
            for line in process.stderr:
                sys.stderr.buffer.write(line)
                if b"Huey consumer started" in line:
                    sys.stderr.flush()
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

        @timeout_after(10, message="Unable to start ragna api")
        def wait_for_ragna_api(poll=0.1):
            url = config.api.url
            while True:
                with contextlib.suppress(httpx.ConnectError):
                    response = httpx.get(url)
                    if response.is_success:
                        return url

                time.sleep(poll)

        yield wait_for_ragna_api()
