"""
helpers for common tasks in the other galleries

"""
import subprocess
import sys
import time
from pathlib import Path
from typing import Collection, Optional, Union

import httpx

from ragna._utils import timeout_after
from ragna.deploy import Config


class RestApi:
    def __init__(
        self,
        *,
        config: Optional[Config] = None,
        extension_modules: Collection[Union[str, Path]] = (),
    ):
        self._process: Optional[subprocess.Popen] = None
        self._config = config or Config()

    def start(self, *, timeout: float = 60) -> None:
        self._process = subprocess.Popen(
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
                print(".", end="")
                time.sleep(1)
            print()

        wait_for_api()

    def stop(self, *, quiet: bool = False) -> None:
        if self._process is None:
            return

        self._process.kill()
        stdout, _ = self._process.communicate()

        if not quiet:
            print(stdout.decode())

    def __del__(self):
        self.stop(quiet=True)
