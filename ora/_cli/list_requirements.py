from collections import defaultdict
from typing import Iterator, Type

from pluggy import PluginManager
from rich.table import Table

from ora._backend import (
    AVAILABLE_SPECNAMES,
    EnvironmentVariableRequirement,
    PackageRequirement,
    Requirement,
)

__all__ = ["make_requirements_tables"]


def make_requirements_tables(plugin_manager: PluginManager) -> Iterator[Table]:
    all_plugins = plugin_manager.get_plugins()
    for plugin in all_plugins:
        table = Table(
            "available",
            "hookimpl",
            "display name",
            "environment variables",
            "packages",
            title=f"module {plugin.__name__} from {plugin.__file__}",
            show_lines=True,
        )

        remove_plugins = all_plugins - {plugin}
        for hookimpl in sorted(AVAILABLE_SPECNAMES):
            hook = plugin_manager.subset_hook_caller(hookimpl, remove_plugins)
            for component_cls in hook():
                reqs = split_requirements(component_cls.requirements())
                table.add_row(
                    yes_or_no(component_cls.is_available()),
                    hookimpl,
                    component_cls.display_name(),
                    format_requirements(reqs[EnvironmentVariableRequirement]),
                    format_requirements(reqs[PackageRequirement]),
                )
            table.add_section()

        yield table


def split_requirements(
    requirements: list[Requirement],
) -> dict[Type[Requirement], Requirement]:
    split_reqs = defaultdict(list)
    for req in requirements:
        split_reqs[type(req)].append(req)
    return split_reqs


def format_requirements(requirements: list[Requirement]):
    if not requirements:
        return "N/A"

    return "\n".join(f"{yes_or_no(req.is_available)} {req}" for req in requirements)


def yes_or_no(condition):
    return ":white_check_mark:" if condition else ":x:"
