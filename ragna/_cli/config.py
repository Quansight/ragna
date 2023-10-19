from collections import defaultdict
from pathlib import Path
from typing import Annotated, Type

import emoji
import questionary
import rich
import typer
from rich.table import Table

import ragna
from ragna.core import (
    Assistant,
    Config,
    EnvVarRequirement,
    PackageRequirement,
    Requirement,
    SourceStorage,
)


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


def config_wizard(*, output_path: Path, force: bool) -> (Config, Path, bool):
    rich.print("\n\t[bold]Welcome to the Ragna config creation wizard![/bold]\n\n")

    intent = questionary.select(
        "Which of the following statements describes best what you want to do?",
        choices=[
            questionary.Choice(
                "I want to try Ragna "
                "without worrying about any additional dependencies or setup.",
                value="demo",
            ),
            questionary.Choice(
                "I want to try Ragna and its builtin components.",
                value="builtin",
            ),
            questionary.Choice(
                "I want to customize the most common parameters.",
                value="common",
            ),
            questionary.Choice(
                "I want to customize everything.",
                value="custom",
            ),
        ],
    ).unsafe_ask()

    config = {
        "demo": _wizard_demo,
        "builtin": _wizard_builtin,
        "common": _wizard_common,
        "custom": _wizard_custom,
    }[intent]()

    if output_path.exists() and not force:
        output_path, force = _handle_output_path(output_path=output_path, force=force)

    return config, output_path, force


def _print_special_config(name):
    rich.print(
        f"For this use case the {name} configuration is the perfect fit!\n"
        f"Hint for the future: the demo configuration can also be accessed by passing "
        f"--config {name} to ragna commands without the need for an actual "
        f"configuration file."
    )


def _wizard_demo() -> Config:
    _print_special_config("demo")
    return Config.demo()


def _wizard_builtin(*, hint_builtin=True) -> Config:
    config = Config.builtin()

    intent = questionary.select(
        "How do you want to select the components?",
        choices=[
            questionary.Choice(
                "I want to use all components for which the requirements are met.",
                value="builtin",
            ),
            questionary.Choice(
                "I want to manually select the components I want to use", value="custom"
            ),
        ],
    ).unsafe_ask()

    if intent == "builtin":
        if hint_builtin:
            _print_special_config("builtin")
        return config

    config.rag.source_storages = _select_components(
        "source storages", ragna.source_storages, SourceStorage
    )
    config.rag.assistants = _select_components(
        "assistants", ragna.assistants, Assistant
    )

    return config


def _select_components(title, module, base_cls):
    selected_components = questionary.checkbox(
        (
            f"ragna has the following {title} builtin. "
            f"Please select the ones you are interested in. "
            f"If the requirements of a selected component ore not met, "
            f"you'll be given more details in a follow-up question."
        ),
        choices=[
            questionary.Choice(
                component.display_name(),
                value=component,
                checked=component.is_available(),
            )
            for component in [
                obj
                for obj in module.__dict__.values()
                if isinstance(obj, type)
                and issubclass(obj, base_cls)
                and obj is not base_cls
            ]
        ],
    ).unsafe_ask()

    for component in [
        component for component in selected_components if not component.is_available()
    ]:
        question = [
            (
                f"The component {component.display_name()} "
                f"has the following requirements that are currently not fully met:"
            ),
            "",
        ]

        requirements = _split_requirements(component.requirements())
        for title, requirement_type in [
            ("Installed packages:", PackageRequirement),
            ("Environment variables:", EnvVarRequirement),
        ]:
            if requirement_type in requirements:
                question.extend(
                    [
                        title,
                        "",
                        _format_requirements(requirements[requirement_type]),
                        "",
                    ]
                )

        question.append(
            f"Are you able to meet these requirements in the future and "
            f"thus want to include {component.display_name()} in the configuration?"
        )

        if not questionary.confirm("\n".join(question)).unsafe_ask():
            selected_components.remove(component)

    return selected_components


def _wizard_common() -> Config:
    config = _wizard_builtin(hint_builtin=False)

    config.local_cache_root = Path(
        questionary.path(
            "Where should local files be stored?", default=str(config.local_cache_root)
        ).unsafe_ask()
    )

    config.rag.queue_url = _select_queue_url(config)

    config.api.url = questionary.text(
        "At what URL do you want the ragna REST API to be served?",
        default=config.api.url,
    ).unsafe_ask()

    if questionary.confirm(
        "Do you want to use a SQL database to persist the chats between runs?",
        default=True,
    ).unsafe_ask():
        config.api.database_url = questionary.text(
            "What is the URL of the database?",
            default=f"sqlite:///{config.local_cache_root / 'ragna.db'}",
        ).unsafe_ask()
    else:
        config.api.database_url = "memory"

    config.ui.url = questionary.text(
        "At what URL do you want the ragna web UI to be served?",
        default=config.ui.url,
    ).unsafe_ask()

    return config


def _select_queue_url(config):
    queue = questionary.select(
        (
            "Ragna internally uses a task queue to perform the RAG workflow. "
            "What kind of queue do you want to use?"
        ),
        # FIXME: include the descriptions as actual descriptions rather than as part
        #  of the title as soon as https://github.com/tmbo/questionary/issues/269 is
        #  resolved.
        choices=[
            questionary.Choice(
                (
                    "memory: Everything runs sequentially on the main thread "
                    "as if there were no task queue."
                ),
                value="memory",
            ),
            questionary.Choice(
                (
                    "file system: The local file system is used to build the queue. "
                    "Starting a ragna worker is required. "
                    "Requires the worker to be run on the same machine as the main "
                    "thread."
                ),
                value="file_system",
            ),
            questionary.Choice(
                (
                    "redis: Redis is used as queue. Starting a ragna worker is "
                    "required."
                ),
                value="redis",
            ),
        ],
    ).unsafe_ask()

    if queue == "memory":
        return "memory"
    elif queue == "file_system":
        return questionary.path(
            "Where do you want to store the queue files?",
            default=str(config.local_cache_root / "queue"),
        ).unsafe_ask()
    elif queue == "redis":
        return questionary.text(
            "What is the URL of the Redis instance?",
            default="redis://127.0.0.1:6379",
        ).unsafe_ask()


def _wizard_custom() -> Config:
    if questionary.confirm(
        (
            "Customizing everything is certainly a valid use case. "
            "However, due to the many available options, "
            "this is not feasible in an interactive wizard. "
            "Please have a look at the documentation instead. "
            "Do you want to create a configuration by customizing the most common "
            "parameters in order to have a basis for the full customization?"
        ),
        default=True,
    ).unsafe_ask():
        return _wizard_common()
    else:
        raise typer.Abort()


def _handle_output_path(*, output_path, force):
    action = questionary.select(
        (
            f"The output path {output_path} already exists "
            f"and you didn't pass the --force flag to overwrite it. "
            f"What do you want to do?"
        ),
        choices=[
            questionary.Choice("Overwrite the existing file.", value="overwrite"),
            questionary.Choice("Select a new output path.", value="new"),
        ],
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
                    ).unsafe_ask()
                )
                .expanduser()
                .resolve()
            )

            if not output_path.exists():
                break

            rich.print(f"The output path {output_path} already exists.")

    return output_path, force


def check_config(config: Config):
    for title, components in [
        ("source storages", config.rag.source_storages),
        ("assistants", config.rag.assistants),
    ]:
        table = Table(
            "",
            "name",
            "environment variables",
            "packages",
            show_lines=True,
            title=title,
        )

        for component in components:
            requirements = _split_requirements(component.requirements())
            table.add_row(
                _yes_or_no(component.is_available()),
                component.display_name(),
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
        return ""

    return "\n".join(f"{_yes_or_no(req.is_available())} {req}" for req in requirements)


def _yes_or_no(condition):
    return emoji.emojize(":check_mark_button:" if condition else ":cross_mark:")
