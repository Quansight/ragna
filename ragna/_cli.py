import itertools
from collections import defaultdict

from typing import Annotated, Optional, Type
from urllib.parse import urlsplit

import typer

import ragna

from ragna.core import Config, EnvVarRequirement, PackageRequirement, Rag, Requirement
from ragna.core._queue import Worker

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


ConfigAnnotated = Annotated[
    Config,
    typer.Option("--config", "-c", metavar="", parser=Config.load_from_source),
]


@app.command(help="List requirements")
def ls(*, config: ConfigAnnotated = "ragna.builtin_config"):
    if not PackageRequirement("rich").is_available():
        print("Please install rich")
        raise typer.Exit(1)

    import rich
    from rich.table import Table

    table = Table(
        "",
        "name",
        "environment variables",
        "packages",
        show_lines=True,
    )

    for name, cls in itertools.chain(
        config.registered_source_storage_classes.items(),
        config.registered_assistant_classes.items(),
    ):
        requirements = _split_requirements(cls.requirements())
        table.add_row(
            _yes_or_no(cls.is_available()),
            name,
            _format_requirements(requirements[EnvVarRequirement]),
            _format_requirements(requirements[PackageRequirement]),
        )

    rich.print(table)


def _split_requirements(
    requirements: list[Requirement],
) -> dict[Type[Requirement], list[Requirement]]:
    split_reqs = defaultdict(list)
    for req in requirements:
        split_reqs[type(req)].append(req)
    return split_reqs


def _format_requirements(requirements: list[Requirement]):
    if not requirements:
        return "N/A"

    return "\n".join(f"{_yes_or_no(req.is_available())} {req}" for req in requirements)


def _yes_or_no(condition):
    return ":white_check_mark:" if condition else ":x:"


@app.command(help="Start Ragna API")
def api(
    *,
    config: ConfigAnnotated = "ragna.builtin_config",
    start_redis_server: Optional[bool] = None,
    start_ragna_worker: bool = True,
):
    required_packages = [
        package
        for package in ["fastapi", "uvicorn"]
        if not PackageRequirement(package).is_available()
    ]
    if required_packages:
        print(f"Please install {', '.join(required_packages)}")
        raise typer.Exit(1)

    import uvicorn

    from ragna._api import api

    rag = Rag(
        config=config,
        start_redis_server=start_redis_server,
        start_ragna_worker=start_ragna_worker,
    )

    components = urlsplit(config.ragna_api_url)
    uvicorn.run(api(rag), host=components.hostname, port=components.port)


@app.command(help="Start Ragna worker(s)")
def worker(
    *,
    # queue_database_url: Annotated[str, typer.Argument()] = "redis://localhost:6379",
    num_workers: Annotated[int, typer.Option("--num-workers", "-n")] = 1,
):
    Worker(num_workers=num_workers).start()
