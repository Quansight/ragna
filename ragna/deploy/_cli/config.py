import itertools
from collections import defaultdict
from pathlib import Path
from types import ModuleType
from typing import Annotated, Iterable, Type, TypeVar, cast

import pydantic
import questionary
import rich
import typer
from rich.markup import escape
from rich.table import Table

import ragna
from ragna.core import (
    Assistant,
    Component,
    EnvVarRequirement,
    PackageRequirement,
    RagnaException,
    Requirement,
    SourceStorage,
)
from ragna.deploy import Config


def parse_config(value: str) -> Config:
    try:
        config = Config.from_file(value)
    except RagnaException:
        rich.print(f"The configuration file {value} does not exist.")
        if value == "./ragna.toml":
            rich.print(
                "If you don't have a configuration file yet, "
                "run [bold]ragna init[/bold] to generate one."
            )
        raise typer.Exit(1)
    except pydantic.ValidationError as validation:
        # FIXME: pretty formatting!
        for error in validation.errors():
            rich.print(error)
        raise typer.Exit(1)
    # This stores the original value so we can pass it on to subprocesses that we might
    # start.
    config.__ragna_cli_config_path__ = value  # type: ignore[attr-defined]
    return config


ConfigOption = Annotated[
    Config,
    typer.Option(
        "-c",
        "--config",
        metavar="CONFIG",
        envvar="RAGNA_CONFIG",
        parser=parse_config,
        help="Path to a Ragna configuration file.",
    ),
]

# This adds a newline before every question to unclutter the output
QMARK = "\n?"


def init_config(*, output_path: Path, force: bool) -> tuple[Config, Path, bool]:
    # FIXME: add link to the config documentation when it is available
    rich.print(
        "\n\t[bold]Welcome to the Ragna config creation wizard![/bold]\n\n"
        "I'll help you create a configuration file to use with ragna.\n"
        "Due to the large amount of parameters, "
        "I unfortunately can't cover everything. "
        "If you want to customize everything, "
        "please have a look at the documentation instead."
    )

    intent = questionary.select(
        "Which of the following statements describes best what you want to do?",
        choices=[
            questionary.Choice(
                (
                    "I want to try Ragna without worrying about any additional "
                    "dependencies or setup."
                ),
                value="demo",
            ),
            questionary.Choice(
                (
                    "I want to try Ragna and its builtin source storages and "
                    "assistants, which potentially require additional dependencies "
                    "or setup."
                ),
                value="builtin",
            ),
            questionary.Choice(
                (
                    "I have used Ragna before and want to customize the most common "
                    "parameters."
                ),
                value="common",
            ),
        ],
        qmark=QMARK,
    ).unsafe_ask()

    wizard = {
        "demo": _wizard_demo,
        "builtin": _wizard_builtin,
        "common": _wizard_common,
    }[intent]
    config = wizard()

    if output_path.exists() and not force:
        output_path, force = _handle_output_path(output_path=output_path, force=force)

    rich.print(
        f"\nAnd with that we are done :tada: "
        f"I'm writing the configuration file to {output_path}."
    )

    return config, output_path, force


def _wizard_demo() -> Config:
    return Config()


def _wizard_builtin() -> Config:
    config = _wizard_demo()

    rich.print(
        "\nragna has the following components builtin. "
        "Select the ones that you want to use. "
        "If the requirements of a selected component are not met, "
        "I'll show you instructions how to meet them later."
    )
    config.source_storages = _select_components(
        "source storages",
        ragna.source_storages,
        SourceStorage,  # type: ignore[type-abstract]
    )
    config.assistants = _select_components(
        "assistants",
        ragna.assistants,
        Assistant,  # type: ignore[type-abstract]
    )

    _handle_unmet_requirements(
        itertools.chain(config.source_storages, config.assistants)
    )

    return config


T = TypeVar("T", bound=Component)


def _select_components(
    title: str,
    module: ModuleType,
    base_cls: Type[T],
) -> list[Type[T]]:
    components = sorted(
        (
            obj
            for obj in module.__dict__.values()
            if isinstance(obj, type)
            and issubclass(obj, base_cls)
            and obj is not base_cls
        ),
        key=lambda component: component.display_name(),
    )
    return cast(
        list[Type[T]],
        questionary.checkbox(
            f"Which {title} do you want to use?",
            choices=[
                questionary.Choice(
                    component.display_name(),
                    value=component,
                    checked=component.is_available(),
                )
                for component in components
            ],
            qmark=QMARK,
        ).unsafe_ask(),
    )


def _handle_unmet_requirements(components: Iterable[Type[Component]]) -> None:
    unmet_requirements = set(
        requirement
        for component in components
        for requirement in component.requirements()
        if not requirement.is_available()
    )
    if not unmet_requirements:
        return

    rich.print(
        "You have selected components, which have additional requirements that are"
        "currently not met."
    )
    unmet_requirements_by_type = _split_requirements(unmet_requirements)

    unmet_package_requirements = sorted(
        str(requirement)
        for requirement in unmet_requirements_by_type[PackageRequirement]
    )
    if unmet_package_requirements:
        rich.print(
            "\nTo use the selected components, "
            "you need to install the following packages: \n"
        )
        for requirement in unmet_package_requirements:
            rich.print(f"- {requirement}")

        rich.print(
            f"\nTo do this, you can run\n\n"
            f"$ pip install {' '.join(unmet_package_requirements)}\n\n"
            f"Optionally, you can also install Ragna with all optional dependencies"
            f"for the builtin components\n\n"
            f"$ pip install '{escape('ragna[all]')}"
        )

    unmet_env_var_requirements = sorted(
        str(requirement)
        for requirement in unmet_requirements_by_type[EnvVarRequirement]
    )
    if unmet_env_var_requirements:
        rich.print(
            "\nTo use the selected components, "
            "you need to set the following environment variables: \n"
        )
        for requirement in unmet_env_var_requirements:
            rich.print(f"- {requirement}")

    rich.print(
        "\nTip: You can check the availability of the requirements with "
        "[bold]ragna check[/bold]."
    )


def _wizard_common() -> Config:
    config = _wizard_builtin()

    config.local_root = Path(
        questionary.path(
            "Where should local files be stored?",
            default=str(config.local_root),
            qmark=QMARK,
        ).unsafe_ask()
    )

    for sub_config, title in [(config.api, "REST API"), (config.ui, "web UI")]:
        sub_config.hostname = questionary.text(  # type: ignore[attr-defined]
            f"What hostname do you want to bind the the Ragna {title} to?",
            default=sub_config.hostname,  # type: ignore[attr-defined]
            qmark=QMARK,
        ).unsafe_ask()

        sub_config.port = int(  # type: ignore[attr-defined]
            questionary.text(
                f"What port do you want to bind the the Ragna {title} to?",
                default=str(sub_config.port),  # type: ignore[attr-defined]
                qmark=QMARK,
            ).unsafe_ask()
        )

    config.api.database_url = questionary.text(
        "What is the URL of the SQL database?",
        default=Config(local_root=config.local_root).api.database_url,
        qmark=QMARK,
    ).unsafe_ask()

    config.api.url = questionary.text(
        "At which URL will the Ragna REST API be served?",
        default=Config(
            api=dict(  # type: ignore[arg-type]
                hostname=config.api.hostname,
                port=config.api.port,
            )
        ).api.url,
        qmark=QMARK,
    ).unsafe_ask()

    config.api.origins = config.ui.origins = [
        questionary.text(
            "At which URL will the Ragna web UI be served?",
            default=Config(
                ui=dict(  # type: ignore[arg-type]
                    hostname=config.ui.hostname,
                    port=config.ui.port,
                )
            ).api.origins[0],
            qmark=QMARK,
        ).unsafe_ask()
    ]

    return config


def _handle_output_path(*, output_path: Path, force: bool) -> tuple[Path, bool]:
    rich.print(
        f"\nThe output path {output_path} already exists "
        f"and you didn't pass the --force flag to overwrite it. "
    )
    action = questionary.select(
        "What do you want to do?",
        choices=[
            questionary.Choice("Overwrite the existing file.", value="overwrite"),
            questionary.Choice("Select a new output path.", value="new"),
        ],
        qmark=QMARK,
    ).unsafe_ask()

    if action == "overwrite":
        force = True
    elif action == "new":
        while True:
            output_path = (
                Path(
                    questionary.path(
                        "Please provide a different output path "
                        "to write the generated config to:",
                        default=str(output_path),
                        qmark=QMARK,
                    ).unsafe_ask()
                )
                .expanduser()
                .resolve()
            )

            if not output_path.exists():
                break

            rich.print(f"The output path {output_path} already exists.")

    return output_path, force


def check_config(config: Config) -> bool:
    fully_available = True

    for title, components in [
        ("source storages", config.source_storages),
        ("assistants", config.assistants),
    ]:
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
    requirements: Iterable[Requirement],
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
