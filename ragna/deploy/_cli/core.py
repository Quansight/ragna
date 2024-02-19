import subprocess
import sys
import time
from pathlib import Path
from typing import Annotated, Optional

import httpx
import rich
import typer
import uvicorn

import ragna
from ragna._utils import timeout_after
from ragna.deploy._api import app as api_app
from ragna.deploy._ui import app as ui_app

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


@app.command(help="Start the REST API.")
def api(
    *,
    config: ConfigOption = "./ragna.toml",  # type: ignore[assignment]
) -> None:
    uvicorn.run(api_app(config), host=config.api.hostname, port=config.api.port)


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
            return httpx.get(config.api.url).is_success
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

            @timeout_after(60)
            def wait_for_api() -> None:
                while not check_api_available():
                    time.sleep(0.5)

            try:
                wait_for_api()
            except TimeoutError:
                rich.print(
                    "Failed to start the API in 60 seconds. "
                    "Please start it manually with [bold]ragna api[/bold]."
                )
                raise typer.Exit(1)

        ui_app(config).serve()  # type: ignore[no-untyped-call]
    finally:
        if process is not None:
            process.kill()
            process.communicate()
