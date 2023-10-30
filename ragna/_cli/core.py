import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Annotated, Optional
from urllib.parse import urlsplit

import httpx
import rich
import typer
import uvicorn

import ragna
from ragna._api import app as api_app
from ragna._ui import app as ui_app
from ragna._utils import timeout_after
from ragna.core._queue import Queue

from .config import ConfigOption, check_config, init_config

app = typer.Typer(
    name="ragna",
    invoke_without_command=True,
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,
)


def version_callback(value: bool) -> None:
    if value:
        rich.print(f"ragna {ragna.__version__} from {ragna.__path__[0]}")
        raise typer.Exit()


@app.callback()
def _main(
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version", callback=version_callback, help="Show version and exit."
        ),
    ] = None,
) -> None:
    pass


@app.command(help="Start a wizard to build a Ragna configuration interactively.")
def init(
    *,
    output_path: Annotated[
        Path,
        typer.Option(
            "-o",
            "--output-file",
            metavar="OUTPUT_PATH",
            default_factory=lambda: Path.cwd() / "ragna.toml",
            show_default="./ragna.toml",
            help="Write configuration to <OUTPUT_PATH>.",
        ),
    ],
    force: Annotated[
        bool,
        typer.Option(
            "-f", "--force", help="Overwrite an existing file at <OUTPUT_PATH>."
        ),
    ] = False,
) -> None:
    config, output_path, force = init_config(output_path=output_path, force=force)
    config.to_file(output_path, force=force)


@app.command(help="Check the availability of components.")
def check(config: ConfigOption = "./ragna.toml") -> None:  # type: ignore[assignment]
    is_available = check_config(config)
    raise typer.Exit(int(not is_available))


@app.command(help="Start workers.")
def worker(
    *,
    config: ConfigOption = "./ragna.toml",  # type: ignore[assignment]
    num_threads: Annotated[
        int,
        typer.Option("--num-threads", "-n", help="Number of worker threads to start."),
    ] = 1,
) -> None:
    if config.core.queue_url == "memory":
        rich.print(f"With {config.core.queue_url=} no worker is required!")
        raise typer.Exit(1)

    queue = Queue(config, load_components=True)
    worker = queue.create_worker(num_threads)

    # FIXME: we need to configure this properly
    logging.basicConfig(level=logging.INFO)
    worker.run()


@app.command(help="Start the REST API.")
def api(
    *,
    config: ConfigOption = "./ragna.toml",  # type: ignore[assignment]
    start_worker: Annotated[
        Optional[bool],
        typer.Option(
            help="Start a ragna worker alongside the REST API in a subprocess.",
            show_default="Start if a non-memory queue is configured.",
        ),
    ] = None,
) -> None:
    if start_worker is None:
        start_worker = config.core.queue_url != "memory"

    components = urlsplit(config.api.url)
    if components.hostname is None or components.port is None:
        # TODO: make this part of the config validation
        rich.print(f"Unable to extract hostname and port from {config.api.url}.")
        raise typer.Exit(1)

    if start_worker:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "ragna",
                "worker",
                "--config",
                config.__ragna_cli_config_path__,  # type: ignore[attr-defined]
            ],
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
    else:
        process = None

    try:
        uvicorn.run(
            api_app(config), host=components.hostname, port=components.port or 31476
        )
    finally:
        if process is not None:
            process.kill()
            process.communicate()


@app.command(help="Start the UI.")
def ui(
    *,
    config: ConfigOption = "./ragna.toml",  # type: ignore[assignment]
    start_api: Annotated[
        Optional[bool],
        typer.Option(
            help="Start the ragna REST API alongside the UI in a subprocess.",
            show_default="Start if the API is not served at the configured URL.",
        ),
    ] = None,
) -> None:
    def check_api_available() -> bool:
        try:
            httpx.get(config.api.url)
            return True
        except httpx.ConnectError:
            return False

    if start_api is None:
        start_api = not check_api_available()

    if start_api:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "ragna",
                "api",
                "--config",
                config.__ragna_cli_config_path__,  # type: ignore[attr-defined]
            ],
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
    else:
        process = None

    try:
        if process is not None:

            @timeout_after(30)
            def wait_for_api() -> None:
                while not check_api_available():
                    time.sleep(0.5)

            wait_for_api()

        ui_app(config).serve()  # type: ignore[no-untyped-call]
    finally:
        if process is not None:
            process.kill()
            process.communicate()
