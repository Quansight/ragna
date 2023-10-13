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
    from ragna.core import Assistant, SourceStorage

    def get_available_components(module, cls):
        return [
            obj
            for obj in module.__dict__.values()
            if isinstance(obj, type) and issubclass(obj, cls) and obj.is_available()
        ]

    config = Config()

    config.rag.queue_url = str(config.local_cache_root / "queue")
    config.rag.source_storages = get_available_components(
        source_storages, SourceStorage
    )
    config.rag.assistants = get_available_components(assistants, Assistant)

    config.api.database_url = f"sqlite:///{config.local_cache_root}/ragna.db"

    return config
