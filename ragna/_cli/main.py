from typing import Annotated, cast, Optional, Type

import typer

from rich.console import Console

import ragna
from ragna._backend import AVAILABLE_SPECNAMES, Component
from ragna._ui import app as ui_app

from .extensions import load_and_register_extensions
from .list_requirements import make_requirements_tables

__all__ = ["app"]

app = typer.Typer(name="ragna", no_args_is_help=True)
console = Console()


def version_callback(value: bool):
    if value:
        print(f"ragna {ragna.__version__}")
        raise typer.Exit()


@app.callback()
def _main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", callback=version_callback),
    ] = None
):
    pass


@app.command()
def launch(
    *,
    extensions: Annotated[
        list[str],
        typer.Option(
            "-e",
            "--extension",
            rich_help_panel="Extensions",
        ),
    ] = ["ragna.extensions"],
    no_deselect: Annotated[
        bool,
        typer.Option(
            "--no-deselect",
            rich_help_panel="Extensions",
        ),
    ] = False,
    url: Annotated[
        str,
        typer.Option(
            envvar="RAGNA_URL",
            rich_help_panel="Deployment",
        ),
    ] = "localhost",
    port: Annotated[
        int,
        typer.Option(
            envvar="RAGNA_PORT",
            rich_help_panel="Deployment",
        ),
    ] = 31476,
    log_level: Annotated[
        str,
        typer.Option(
            envvar="RAGNA_LOG_LEVEL",
            rich_help_panel="Deployment",
        ),
    ] = "INFO",
):
    plugin_manager = load_and_register_extensions(extensions)

    # FIXME: set log_level

    components = {specname: {} for specname in AVAILABLE_SPECNAMES}
    for specname in components:
        for component_cls in cast(
            list[Type[Component]], getattr(plugin_manager.hook, specname)()
        ):
            name = component_cls.display_name()
            if not component_cls.is_available():
                if no_deselect:
                    # FIXME: this should be logged
                    console.print(f"{name} is not available")
                    raise typer.Exit(1)
                else:
                    continue

            components[specname][name] = component_cls()

    ui_app(
        doc_dbs=components["ragna_doc_db"],
        llms=components["ragna_llm"],
        url=url,
        port=port,
    )


@app.command()
def list_requirements(
    *,
    extensions: Annotated[
        list[str],
        typer.Option(
            "-e",
            "--extension",
        ),
    ] = ["ragna.extensions"],
):
    plugin_manager = load_and_register_extensions(extensions)

    console = Console()
    for table in make_requirements_tables(plugin_manager):
        console.print(table)
        console.print()
