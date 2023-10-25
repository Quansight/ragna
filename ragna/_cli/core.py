import logging
import subprocess
import sys
from pathlib import Path
from typing import Annotated, Optional
from urllib.parse import urlsplit

import rich
import typer
import uvicorn

import ragna
from ragna._api import app as api_app
from ragna.core._queue import Queue

from .config import (
    COMMON_CONFIG_OPTION_ARGS,
    COMMON_CONFIG_OPTION_KWARGS,
    ConfigOption,
    check_config,
    config_wizard,
)

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


@app.command(help="Create or check configurations.")
def config(
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
    config: Annotated[
        Optional[ragna.Config],
        typer.Option(
            *COMMON_CONFIG_OPTION_ARGS,
            **COMMON_CONFIG_OPTION_KWARGS,
            show_default="Start a wizard to build the configuration interactively.",
        ),
    ] = None,
    check: Annotated[
        bool,
        typer.Option(
            "--check",
            help=(
                "Display the availability for all selected components in <CONFIG>. "
                "If given, no file is generated at <OUTPUT_PATH>."
            ),
        ),
    ] = False,
    force: Annotated[
        bool,
        typer.Option(
            "-f", "--force", help="Overwrite an existing file at <OUTPUT_PATH>."
        ),
    ] = False,
) -> None:
    if config is None:
        if check:
            rich.print(
                "--check makes no sense without passing a config with -c / --config"
            )
            raise typer.Exit(1)
        config, output_path, force = config_wizard(output_path=output_path, force=force)

    if check:
        is_available = check_config(config)
        raise typer.Exit(int(not is_available))

    config.to_file(output_path, force=force)


@app.command(help="Start workers.")
def worker(
    *,
    config: ConfigOption = "builtin",  # type: ignore[assignment]
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
    config: ConfigOption = "builtin",  # type: ignore[assignment]
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

    if start_worker:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "ragna",
                "worker",
                "--config",
                config.__ragna_cli_value__,  # type: ignore[attr-defined]
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    else:
        process = None

    try:
        components = urlsplit(config.api.url)
        if components.hostname is None or components.port is None:
            # TODO: make this part of the config validation
            rich.print(f"Unable to extract hostname and port from {config.api.url}.")
            raise typer.Exit(1)

        uvicorn.run(
            api_app(config), host=components.hostname, port=components.port or 31476
        )
    finally:
        if process is not None:
            process.kill()
            process.communicate()
