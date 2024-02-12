import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import httpx

from ragna._utils import timeout_after
from ragna.deploy import Config

__all__ = ["assets", "RestApi"]

assets = Path(__file__).parent / "assets"


class RestApi:
    def __init__(self, config: Config):
        self._process: Optional[subprocess.Popen] = None
        self._config = config

    def start(self, *, timeout: float = 60) -> None:
        process = subprocess.Popen(
            [sys.executable, "-m", "ragna", "api"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        def check_api_available() -> bool:
            try:
                return httpx.get(self._config.api.url).is_success
            except httpx.ConnectError:
                return False

        @timeout_after(timeout, message="Failed to the start the Ragna REST API")
        def wait_for_api() -> None:
            print("Starting Ragna REST API")
            while not check_api_available():
                # FIXME: use communicate with timeout here and raise if it failed already
                time.sleep(1)
                print(".", end="")

            print()

        wait_for_api()
        self._process = process

    def stop(self, *, quiet: bool = False) -> None:
        self._process.kill()
        stdout, _ = self._process.communicate()

        if not quiet:
            print(stdout.decode())

    def __del__(self):
        if self._process is not None:
            self.stop(quiet=True)
