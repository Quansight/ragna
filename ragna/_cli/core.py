import logging
import subprocess
import sys
from pathlib import Path
from typing import Annotated, Optional
from urllib.parse import urlsplit

import typer

import ragna
from ragna.core import PackageRequirement
from ragna.core._queue import Queue
from .config import (
    check_config,
    COMMON_CONFIG_OPTION_ARGS,
    COMMON_CONFIG_OPTION_KWARGS,
    config_wizard,
    ConfigOption,
)

app = typer.Typer(
    name="ragna",
    invoke_without_command=True,
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,
)


def version_callback(value: bool):
    if value:
        print(f"ragna {ragna.__version__} from {ragna.__path__[0]}")
        raise typer.Exit()


@app.callback()
def _main(
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version", callback=version_callback, help="Show version and exit."
        ),
    ] = None
):
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
        ragna.Config,
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
):
    if config is None:
        config = config_wizard()

    if check:
        is_available = check_config(config)
        raise typer.Exit(int(not is_available))

    config.to_file(output_path, force=force)


@app.command(help="Start workers.")
def worker(
    *,
    config: ConfigOption = "builtin",
    num_threads: Annotated[
        int,
        typer.Option("--num-threads", "-n", help="Number of worker threads to start."),
    ] = 1,
):
    if config.rag.queue_url == "memory":
        print(f"With {config.rag.queue_url=} no worker is required!")
        raise typer.Exit(1)

    queue = Queue(config, load_components=True)
    worker = queue.create_worker(num_threads)

    # FIXME: we need to configure this properly
    logging.basicConfig(level=logging.INFO)
    worker.run()


@app.command(help="Start the REST API.")
def api(
    *,
    config: ConfigOption = "builtin",
    start_worker: Annotated[
        bool,
        typer.Option(
            help="Start a ragna worker alongside the REST API in a subprocess.",
            show_default="Start if a non-memory queue is configured.",
        ),
    ] = None,
):
    required_packages = [
        package
        for package in ["fastapi", "uvicorn"]
        if not PackageRequirement(package).is_available()
    ]
    if required_packages:
        print(f"Please install {', '.join(required_packages)}")
        raise typer.Exit(1)

    if start_worker is None:
        start_worker = config.rag.queue_url != "memory"
    if start_worker:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "ragna",
                "worker",
                "--config",
                config.__ragna_cli_value__,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    else:
        process = None

    import uvicorn

    from ragna._api import api

    try:
        components = urlsplit(config.api.url)
        uvicorn.run(api(config), host=components.hostname, port=components.port)
    finally:
        if process is not None:
            process.kill()
            process.communicate()
