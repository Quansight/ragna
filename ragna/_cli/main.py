from collections import defaultdict

from pathlib import Path
from typing import Annotated, cast, Optional, Type

import typer

from rich.console import Console

import ragna
from ragna._backend import AVAILABLE_SPECNAMES, Component
from ragna._ui import app as ui_app, AppComponents, AppConfig

from .extensions import load_and_register_extensions
from .list_requirements import make_requirements_tables

__all__ = ["app"]

app = typer.Typer(
    name="ragna",
    invoke_without_command=True,
    no_args_is_help=True,
    add_completion=False,
)
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
    cache_root: Annotated[
        Path,
        typer.Option(
            envvar="RAGNA_CACHE_ROOT",
            rich_help_panel="Deployment",
        ),
    ] = Path.home()
    / ".cache"
    / "ragna",
):
    plugin_manager = load_and_register_extensions(extensions)

    # FIXME: set log_level

    app_config = AppConfig(url=url, port=port, cache_root=cache_root)

    components = defaultdict(dict)
    deselected = False
    for specname in AVAILABLE_SPECNAMES:
        components_attribute_name = f"{specname.removeprefix('ragna_')}s"

        for component_cls in cast(
            list[Type[Component]], getattr(plugin_manager.hook, specname)()
        ):
            name = component_cls.display_name()
            if not component_cls.is_available():
                # FIXME: this should be logged
                print(f"{name} is not available")
                deselected = True
                continue

            components[components_attribute_name][name] = component_cls(app_config)

    if deselected and no_deselect:
        print("Needed to deselect at least one component")
        raise SystemExit(1)

    components = AppComponents(**components)

    ui_app(app_config=app_config, components=components)


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
