import importlib
import importlib.util
from pathlib import Path
from types import ModuleType

from typing import Annotated

import typer

from pluggy import PluginManager

from ragna._backend import hookspecs


Extensions = Annotated[
    list[str],
    typer.Option(
        "-e",
        "--extension",
        help=(
            "Extension to load. "
            "Can be a path to a python module or the name of an importable package. "
            "Can be given multiple times."
        ),
        rich_help_panel="Extensions",
    ),
]


def load_and_register_extensions(extensions: list[str]) -> PluginManager:
    plugin_manager = PluginManager("ragna")
    plugin_manager.add_hookspecs(hookspecs)

    for extension in extensions:
        plugin_manager.register(load_extension(extension))

    return plugin_manager


def load_extension(source: str) -> ModuleType:
    path = Path(source).expanduser().resolve()
    if path.exists():
        spec = importlib.util.spec_from_file_location(path.name, path)
        if not spec or not spec.loader:
            raise Exception("ADDME")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    else:
        module = importlib.import_module(source)

    return module
