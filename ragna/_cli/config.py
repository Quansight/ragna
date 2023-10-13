from collections import defaultdict

from typing import Annotated, Type

import typer

import ragna

from ragna.core import Config, Requirement


def parse_config(value: str) -> Config:
    if value == "demo":
        config = Config()
    elif value == "builtin":
        config = ragna.builtin_config()
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
        "If 'builtin', loads a configuration with all available builtin components."
    ),
)
ConfigOption = Annotated[
    ragna.Config,
    typer.Option(*COMMON_CONFIG_OPTION_ARGS, **COMMON_CONFIG_OPTION_KWARGS),
]


def config_wizard() -> Config:
    # FIXME
    return Config()


def check_config():
    print("all good!")
    # config = json.loads(Config().model_dump_json())
    # confg = Config().model_dump()
    # # FIXME: handle secrets either plain or not at all
    #
    # a = tomlkit.dumps(confg)
    # print(a)
    #
    # # a = tomlkit.TOMLDocument.fromkeys(list(config.keys()), list(config.values()))
    #
    # print(tomlkit.dumps(a))

    # if not PackageRequirement("rich").is_available():
    #     print("Please install rich")
    #     raise typer.Exit(1)
    #
    # import rich
    # from rich.table import Table
    #
    # table = Table(
    #     "",
    #     "name",
    #     "environment variables",
    #     "packages",
    #     show_lines=True,
    # )
    #
    # for name, cls in itertools.chain(
    #     config.registered_source_storage_classes.items(),
    #     config.registered_assistant_classes.items(),
    # ):
    #     requirements = _split_requirements(cls.requirements())
    #     table.add_row(
    #         _yes_or_no(cls.is_available()),
    #         name,
    #         _format_requirements(requirements[EnvVarRequirement]),
    #         _format_requirements(requirements[PackageRequirement]),
    #     )
    #
    # rich.print(table)
    pass


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
