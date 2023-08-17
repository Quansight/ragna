import importlib
import importlib.util
from pathlib import Path
from types import ModuleType

from pluggy import PluginManager

from ragna._backend import hookspecs

__all__ = ["load_and_register_extensions"]


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
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    else:
        module = importlib.import_module(source)

    return module
