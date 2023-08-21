from pathlib import Path
from typing import Annotated, cast, Optional, Type

import typer

from rich.console import Console

import ragna
from ragna._backend import AVAILABLE_SPECNAMES, Component
from ragna._ui import app as ui_app, AppComponents, AppConfig

from .extensions import Extensions, load_and_register_extensions
from .list_requirements import make_requirements_tables

__all__ = ["app"]

app = typer.Typer(
    name="ragna",
    invoke_without_command=True,
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,
)
console = Console()


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


@app.command(help="Launch the web UI.")
def launch(
    *,
    extensions: Extensions = ["ragna.extensions"],
    no_deselect: Annotated[
        bool,
        typer.Option(
            "--no-deselect",
            help="Error if one or more components are not available.",
            rich_help_panel="Extensions",
        ),
    ] = False,
    url: Annotated[
        str,
        typer.Option(
            help="URL of the web UI",
            envvar="RAGNA_URL",
            rich_help_panel="Deployment",
        ),
    ] = "localhost",
    port: Annotated[
        int,
        typer.Option(
            help="Port of the web UI.",
            envvar="RAGNA_PORT",
            rich_help_panel="Deployment",
        ),
    ] = 31476,
    log_level: Annotated[
        str,
        typer.Option(
            help="Minimum level of messages that will be logged.",
            envvar="RAGNA_LOG_LEVEL",
            rich_help_panel="Deployment",
        ),
    ] = "INFO",
    cache_root: Annotated[
        Path,
        typer.Option(
            help="Location of cache directory for ragna components.",
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

    components = {specname: {} for specname in AVAILABLE_SPECNAMES}
    deselected = False
    for specname in components:
        for component_cls in cast(
            list[Type[Component]], getattr(plugin_manager.hook, specname)()
        ):
            name = component_cls.display_name()
            if not component_cls.is_available():
                # FIXME: this should be logged as warning
                print(f"{name} is not available")
                deselected = True
                continue

            components[specname][name] = component_cls(app_config)

    if deselected and no_deselect:
        print("One or more components were deselected. Run ragna ls for details.")
        raise typer.Exit(1)

    component_unavailable = False
    for specname, available_components in components.items():
        if not available_components:
            # FIXME: this should be logged as error
            print(f"No component available for hookimpl '{specname}'.")
            component_unavailable = True
    if component_unavailable:
        raise typer.Exit(1)

    ui_app(
        app_config=app_config,
        components=AppComponents(
            **{
                # remove the 'ragna_' prefix and append an 's', e.g.
                # 'ragna_llm' -> 'llms'
                f"{specname.removeprefix('ragna_')}s": component
                for specname, component in components.items()
            }
        ),
    )


@app.command(help="List all extensions and their requirements.")
def ls(*, extensions: Extensions = ["ragna.extensions"]):
    plugin_manager = load_and_register_extensions(extensions)

    console = Console()
    for table in make_requirements_tables(plugin_manager):
        console.print(table)
        console.print()
