try:
    from ._version import __version__
except ModuleNotFoundError:
    import warnings

    warnings.warn("ragna was not properly installed!")
    del warnings

    __version__ = "UNKNOWN"

from . import assistants, core, source_storages, utils

from .core import Config, Rag


def builtin_config():
    from ragna.core import Assistant, RagConfig, SourceStorage

    def get_available_components(module, cls):
        return [
            f"{obj.__module__}.{obj.__qualname__}"
            for obj in module.__dict__.values()
            if isinstance(obj, type) and issubclass(obj, cls) and obj.is_available()
        ]

    config = Config()
    config.rag = RagConfig(
        database_url=f"sqlite:///{config.local_cache_root}/ragna.db",
        queue_url=config.local_cache_root / "queue",
        source_storages=get_available_components(source_storages, SourceStorage),
        assistants=get_available_components(assistants, Assistant),
    )
    return config


builtin_config = builtin_config()
