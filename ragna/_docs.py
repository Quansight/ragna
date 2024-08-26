import atexit
import inspect
import itertools
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any, Optional, cast

import httpx

from ragna._utils import timeout_after
from ragna.core import RagnaException
from ragna.deploy import Config

__all__ = ["SAMPLE_CONTENT", "RestApi"]

SAMPLE_CONTENT = """\
Ragna is an open source project built by Quansight. It is designed to allow
organizations to explore the power of Retrieval-augmented generation (RAG) based
AI tools. Ragna provides an intuitive API for quick experimentation and built-in
tools for creating production-ready applications allowing you to quickly leverage
Large Language Models (LLMs) for your work.

The Ragna website is https://ragna.chat/. The source code is available at
https://github.com/Quansight/ragna under the BSD 3-Clause license.
"""


class RestApi:
    def __init__(self) -> None:
        self._process: Optional[subprocess.Popen] = None
        # In case the documentation errors before we call RestApi.stop, we still need to
        # stop the server to avoid zombie processes
        atexit.register(self.stop, quiet=True)

    def start(
        self,
        config: Config,
        *,
        authenticate: bool = False,
        upload_document: bool = False,
    ) -> tuple[httpx.Client, Optional[dict]]:
        if upload_document and not authenticate:
            raise RagnaException(
                "Cannot upload a document without authenticating first. "
                "Set authenticate=True when using upload_document=True."
            )
        python_path, config_path = self._prepare_config(config)

        client = httpx.Client(base_url=config.api.url)

        self._process = self._start_api(config_path, python_path, client)

        if authenticate:
            self._authenticate(client)

        if upload_document:
            document = self._upload_document(client)
        else:
            document = None

        return client, document

    def _prepare_config(self, config: Config) -> tuple[str, str]:
        deploy_directory = Path(tempfile.mkdtemp())

        python_path = (
            f"{deploy_directory}{os.pathsep}{os.environ.get('PYTHONPATH', '')}"
        )
        config_path = str(deploy_directory / "ragna.toml")

        config.local_root = deploy_directory
        config.api.database_url = f"sqlite:///{deploy_directory / 'ragna.db'}"

        sys.modules["__main__"].__file__ = inspect.getouterframes(
            inspect.currentframe()
        )[2].filename
        custom_module = deploy_directory.name
        custom_components = set()
        with open(deploy_directory / f"{custom_module}.py", "w") as file:
            # FIXME Find a way to automatically detect necessary imports
            file.write("import uuid; from uuid import *\n")
            file.write("import textwrap; from textwrap import*\n")
            file.write("from typing import *\n")
            file.write("from ragna import *\n")
            file.write("from ragna.core import *\n")

            for component in itertools.chain(config.source_storages, config.assistants):
                if component.__module__ == "__main__":
                    custom_components.add(component)
                    file.write(f"{textwrap.dedent(inspect.getsource(component))}\n\n")
                    component.__module__ = custom_module

        config.to_file(config_path)

        for component in custom_components:
            component.__module__ = "__main__"

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

    def _upload_document(self, client: httpx.Client) -> dict[str, Any]:
        name, content = "ragna.txt", SAMPLE_CONTENT

        response = client.post("/document", json={"name": name}).raise_for_status()
        document_upload = response.json()

        document = cast(dict[str, Any], document_upload["document"])

        parameters = document_upload["parameters"]
        client.request(
            parameters["method"],
            parameters["url"],
            data=parameters["data"],
            files={"file": content},
        ).raise_for_status()

        return document

    def stop(self, *, quiet: bool = False) -> None:
        if self._process is None:
            return

        self._process.terminate()
        stdout, _ = self._process.communicate()

        if not quiet:
            print(stdout.decode())
