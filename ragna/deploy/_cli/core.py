import signal
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
    ignore_unavailable_components: Annotated[
        bool,
        typer.Option(
            help=(
                "Ignore components that are not available, "
                "i.e. their requirements are not met. "
            )
        ),
    ] = False,
) -> None:
    uvicorn.run(
        api_app(
            config=config, ignore_unavailable_components=ignore_unavailable_components
        ),
        host=config.api.hostname,
        port=config.api.port,
    )


@app.command(help="Start the web UI.")
def ui(
    *,
    config: ConfigOption = "./ragna.toml",  # type: ignore[assignment]
    start_api: Annotated[
        Optional[bool],
        typer.Option(
            help="Start the ragna REST API alongside the web UI in a subprocess.",
            show_default="Start if the API is not served at the configured URL.",
        ),
    ] = None,
    ignore_unavailable_components: Annotated[
        bool,
        typer.Option(
            help=(
                "Ignore components that are not available, "
                "i.e. their requirements are not met. "
                "This option as no effect if --no-start-api is used."
            )
        ),
    ] = False,
    open_browser: Annotated[
        bool,
        typer.Option(help="Open the web UI in the browser when it is started."),
    ] = True,
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
                f"--{'' if ignore_unavailable_components else 'no-'}ignore-unavailable-components",
            ],
            stdout=sys.stdout,
            stderr=sys.stderr,
        )

        def shutdown_api() -> None:
            process.terminate()
            process.communicate()

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
            shutdown_api()
            raise typer.Exit(1)
    else:
        shutdown_api = lambda: None  # noqa: E731

    # By default Python does not handle the SIGTERM signal. Meaning, by default it would
    # terminate the running process, i.e. the UI server, but not would not trigger the
    # finally branch below and leave the API server running in case we have started it
    # in a subprocess here.
    # Thus, we turn SIGTERM in a regular exit, which gracefully triggers the finally
    # branch.
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit())

    try:
        ui_app(config=config, open_browser=open_browser).serve()  # type: ignore[no-untyped-call]
    finally:
        shutdown_api()
