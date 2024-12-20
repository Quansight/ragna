from pathlib import Path
from typing import Annotated, Optional

import rich
import typer
import uvicorn

import ragna
from ragna.deploy._core import make_app

from .config import ConfigOption, check_config, init_config
from .corpus import app as corpus_app

app = typer.Typer(
    name="Ragna",
    invoke_without_command=True,
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,
)
app.add_typer(corpus_app)


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


@app.command(help="Deploy Ragna REST API and web UI.")
def deploy(
    *,
    config: ConfigOption = "./ragna.toml",  # type: ignore[assignment]
    api: Annotated[
        bool,
        typer.Option(
            "--api/--no-api",
            help="Deploy the Ragna REST API.",
        ),
    ] = True,
    ui: Annotated[
        bool,
        typer.Option(
            help="Deploy the Ragna web UI.",
        ),
    ] = True,
    ignore_unavailable_components: Annotated[
        bool,
        typer.Option(
            help=(
                "Ignore components that are not available, "
                "i.e. their requirements are not met. "
            )
        ),
    ] = False,
    open_browser: Annotated[
        Optional[bool],
        typer.Option(
            help="Open a browser when Ragna is deployed.",
            show_default="value of ui / no-ui",
        ),
    ] = None,
) -> None:
    if not (api or ui):
        raise Exception

    if open_browser is None:
        open_browser = ui

    uvicorn.run(
        lambda: make_app(
            config,
            ui=ui,
            api=api,
            ignore_unavailable_components=ignore_unavailable_components,
            open_browser=open_browser,
        ),
        factory=True,
        host=config.hostname,
        port=config.port,
    )
