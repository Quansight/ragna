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

from ragna.core import RagnaException
from ragna.deploy import Config

from ._utils import BackgroundSubprocess

__all__ = ["SAMPLE_CONTENT", "RagnaDeploy"]

SAMPLE_CONTENT = """\
Ragna is an open source project built by Quansight. It is designed to allow
organizations to explore the power of Retrieval-augmented generation (RAG) based
AI tools. Ragna provides an intuitive API for quick experimentation and built-in
tools for creating production-ready applications allowing you to quickly leverage
Large Language Models (LLMs) for your work.

The Ragna website is https://ragna.chat/. The source code is available at
https://github.com/Quansight/ragna under the BSD 3-Clause license.
"""


class RagnaDeploy:
    def __init__(self, config: Config) -> None:
        self.config = config
        python_path, config_path = self._prepare_config()
        self._process = self._deploy(config, config_path, python_path)
        # In case the documentation errors before we call RagnaDeploy.terminate,
        # we still need to stop the server to avoid zombie processes
        atexit.register(self.terminate, quiet=True)

    def _prepare_config(self) -> tuple[str, str]:
        deploy_directory = Path(tempfile.mkdtemp())

        python_path = os.pathsep.join(
            [str(deploy_directory), os.environ.get("PYTHONPATH", "")]
        )
        config_path = str(deploy_directory / "ragna.toml")

        self.config.local_root = deploy_directory
        self.config.database_url = f"sqlite:///{deploy_directory / 'ragna.db'}"

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

            for component in itertools.chain(
                self.config.source_storages, self.config.assistants
            ):
                if component.__module__ == "__main__":
                    custom_components.add(component)
                    file.write(f"{textwrap.dedent(inspect.getsource(component))}\n\n")
                    component.__module__ = custom_module

        self.config.to_file(config_path)

        for component in custom_components:
            component.__module__ = "__main__"

        return python_path, config_path

    def _deploy(
        self, config: Config, config_path: str, python_path: str
    ) -> BackgroundSubprocess:
        env = os.environ.copy()
        env["PYTHONPATH"] = python_path

        def startup_fn() -> bool:
            try:
                return httpx.get(f"{config._url}/health").is_success
            except httpx.ConnectError:
                return False

        if startup_fn():
            raise RagnaException("ragna server is already running")

        return BackgroundSubprocess(
            sys.executable,
            "-m",
            "ragna",
            "deploy",
            "--api",
            "--no-ui",
            "--config",
            config_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            startup_fn=startup_fn,
            startup_timeout=60,
        )

    def get_http_client(
        self,
        *,
        authenticate: bool = False,
        upload_sample_document: bool = False,
    ) -> tuple[httpx.Client, Optional[dict[str, Any]]]:
        if upload_sample_document and not authenticate:
            raise RagnaException(
                "Cannot upload a document without authenticating first. "
                "Set authenticate=True when using upload_sample_document=True."
            )

        client = httpx.Client(base_url=self.config._url)

        if authenticate:
            client.get("/login", follow_redirects=True)

        if upload_sample_document:
            name, content = "ragna.txt", SAMPLE_CONTENT

            response = client.post(
                "/api/documents", json=[{"name": name}]
            ).raise_for_status()
            document = cast(dict[str, Any], response.json()[0])

            client.put(
                "/api/documents",
                files=[("documents", (document["id"], content.encode()))],
            )
        else:
            document = None

        return client, document

    def terminate(self, quiet: bool = False) -> None:
        if self._process is None:
            return

        output = self._process.terminate()

        if output and not quiet:
            stdout, _ = output
            print(stdout)
