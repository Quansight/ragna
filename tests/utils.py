import contextlib
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
