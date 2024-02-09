import subprocess
import sys
import time
from pathlib import Path
from typing import Collection, Optional, Union

import httpx

from ragna._utils import timeout_after
from ragna.deploy import Config


# make it an asset!
def make_demo_document(path: Union[str, Path]) -> str:
    content = """\
Ragna is an open source project built by Quansight. It is designed to allow
organizations to explore the power of Retrieval-augmented generation (RAG) based
AI tools. Ragna provides an intuitive API for quick experimentation and built-in
tools for creating production-ready applications allowing you to quickly leverage
Large Language Models (LLMs) for your work.

The Ragna website is https://ragna.chat/. The source code is available at
https://github.com/Quansight/ragna under the BSD 3-Clause license.
"""
    with open(path, "w") as file:
        file.write(content)
    return content


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
