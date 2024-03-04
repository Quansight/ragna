import inspect
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

import httpx

from ragna._utils import timeout_after
from ragna.deploy import Config

__all__ = ["assets", "RestApi"]

assets = Path(__file__).parent / "assets"


class RestApi:
    def __init__(self):
        self._process: Optional[subprocess.Popen] = None

    def start(self, config: Config, *, authenticate: bool = False) -> httpx.Client:
        python_path, config_path = self._prepare_config(config)

        client = httpx.Client(base_url=config.api.url)

        self._process = self._start_api(config_path, python_path, client)

        if authenticate:
            self._authenticate(client)

        return client

    def _prepare_config(self, config: Config) -> tuple[str, str]:
        deploy_directory = Path(tempfile.mkdtemp())

        python_path = (
            f"{deploy_directory}{os.pathsep}{os.environ.get('PYTHONPATH', '')}"
        )
        config_path = str(deploy_directory / "ragna.toml")

        config.local_root = deploy_directory

        sys.modules["__main__"].__file__ = inspect.getouterframes(
            inspect.currentframe()
        )[2].filename
        custom_module = deploy_directory.name
        with open(deploy_directory / f"{custom_module}.py", "w") as file:
            # TODO: this currently only handles assistants. When needed, we can extend
            #  to source storages.
            file.write("from ragna import assistants\n\n")

            for assistant in config.assistants:
                if assistant.__module__ == "__main__":
                    file.write(f"{inspect.getsource(assistant)}\n\n")
                    assistant.__module__ = custom_module

        config.to_file(config_path)
        return python_path, config_path

    def _start_api(
        self, config_path: str, python_path: str, client: httpx.Client
    ) -> subprocess.Popen:
        env = os.environ.copy()
        env["PYTHONPATH"] = python_path

        process = subprocess.Popen(
            [sys.executable, "-m", "ragna", "api", "--config", config_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

        def check_api_available() -> bool:
            try:
                return client.get("/").is_success
            except httpx.ConnectError:
                return False

        failure_message = "Failed to the start the Ragna REST API."

        @timeout_after(60, message=failure_message)
        def wait_for_api() -> None:
            print("Starting Ragna REST API")
            while not check_api_available():
                try:
                    stdout, stderr = process.communicate(timeout=1)
                except subprocess.TimeoutExpired:
                    print(".", end="")
                    continue
                else:
                    parts = [failure_message]
                    if stdout:
                        parts.append(f"\n\nSTDOUT:\n\n{stdout.decode()}")
                    if stderr:
                        parts.append(f"\n\nSTDERR:\n\n{stderr.decode()}")

                    raise RuntimeError("".join(parts))

            print()

        wait_for_api()
        return process

    def _authenticate(self, client: httpx.Client) -> None:
        username = password = "Ragna"

        response = client.post(
            "/token",
            data={"username": username, "password": password},
        ).raise_for_status()
        token = response.json()

        client.headers["Authorization"] = f"Bearer {token}"

    def stop(self, *, quiet: bool = False) -> None:
        self._process.kill()
        stdout, _ = self._process.communicate()

        if not quiet:
            print(stdout.decode())

    def __del__(self):
        if self._process is not None:
            self.stop(quiet=True)
