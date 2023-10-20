from collections import defaultdict
from typing import Annotated, cast, Type, TYPE_CHECKING

import rich
import typer
from rich.table import Table

import ragna
from ragna.core import Config, EnvVarRequirement, PackageRequirement, Requirement

if TYPE_CHECKING:
    pass


def parse_config(value: str) -> Config:
    if value == "demo":
        config = Config.demo()
    elif value == "builtin":
        config = Config.builtin()
    else:
        config = Config.from_file(value)
    config.__ragna_cli_value__ = value
    return config


COMMON_CONFIG_OPTION_ARGS = ("-c", "--config")
COMMON_CONFIG_OPTION_KWARGS = dict(
    metavar="CONFIG",
    envvar="RAGNA_CONFIG",
    parser=parse_config,
    help=(
        "Configuration to use. "
        "Can be path to a Ragna configuration file, 'demo', or 'builtin'.\n\n"
        "If 'demo', loads a minimal configuration without persistent state.\n\n"
        "If 'builtin', loads a configuration with all available builtin components, "
        "but without extra infrastructure requirements."
    ),
)
ConfigOption = Annotated[
    ragna.Config,
    typer.Option(*COMMON_CONFIG_OPTION_ARGS, **COMMON_CONFIG_OPTION_KWARGS),
]


def config_wizard() -> Config:
    print(
        "Unfortunately, we over-promised here. There is no interactive wizard yet :( "
        "Continuing with the deme configuration."
    )
    return Config.demo()


def check_config(config: Config) -> bool:
    fully_available = True

    for title, components in [
        ("source storages", config.rag.source_storages),
        ("assistants", config.rag.assistants),
    ]:
        if TYPE_CHECKING:
            from ragna.core._components import Component

            components = cast(list[Type[Component]], components)

        table = Table(
            "",
            "name",
            "environment variables",
            "packages",
            show_lines=True,
            title=title,
        )

        for component in components:
            is_available = component.is_available()
            fully_available &= is_available

            requirements = _split_requirements(component.requirements())
            table.add_row(
                _yes_or_no(is_available),
                component.display_name(),
                _format_requirements(requirements[EnvVarRequirement]),
                _format_requirements(requirements[PackageRequirement]),
            )

        rich.print(table)

    return fully_available


def _split_requirements(
    requirements: list[Requirement],
) -> dict[Type[Requirement], list[Requirement]]:
    split_reqs = defaultdict(list)
    for req in requirements:
        split_reqs[type(req)].append(req)
    return split_reqs


def _format_requirements(requirements: list[Requirement]) -> str:
    if not requirements:
        return ""

    return "\n".join(f"{_yes_or_no(req.is_available())} {req}" for req in requirements)


def _yes_or_no(condition: bool) -> str:
    return ":white_check_mark:" if condition else ":x:"
