from pathlib import Path
from typing import Annotated, Optional

import httpx
import rich
import typer
import uvicorn

import ragna
from ragna.deploy._core import make_app

from .config import ConfigOption, check_config, init_config

cli = typer.Typer(
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


@cli.callback()
def _main(
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version", callback=version_callback, help="Show version and exit."
        ),
    ] = None,
) -> None:
    pass


@cli.command(help="Start a wizard to build a Ragna configuration interactively.")
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


@cli.command(help="Check the availability of components.")
def check(config: ConfigOption = "./ragna.toml") -> None:  # type: ignore[assignment]
    is_available = check_config(config)
    raise typer.Exit(int(not is_available))


@cli.command(help="Deploy Ragna REST API and web UI.")
def deploy(
    *,
    config: ConfigOption = "./ragna.toml",  # type: ignore[assignment]
    # FIXME: --add no-deploy-api
    deploy_api: Annotated[
        Optional[bool],
        typer.Option(
            "--deploy-api/--no-deploy-api",
            help="Deploy the Ragna REST API.",
            show_default="True if UI is not deployed and otherwise check availability",
        ),
    ] = None,
    deploy_ui: Annotated[
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
) -> None:
    if deploy_api is None:

        def api_available() -> bool:
            try:
                return httpx.get(config.api.url).is_success
            except httpx.ConnectError:
                return False

        deploy_api = not api_available() if deploy_ui else True

    uvicorn.run(
        make_app(
            config,
            deploy_ui=deploy_ui,
            deploy_api=deploy_api,
            ignore_unavailable_components=ignore_unavailable_components,
        ),
        host=config.api.hostname,
        port=config.api.port,
    )
