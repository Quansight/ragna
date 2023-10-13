try:
    from ._version import __version__
except ModuleNotFoundError:
    import warnings

    warnings.warn("ragna was not properly installed!")
    del warnings

    __version__ = "UNKNOWN"

from . import assistant, core, source_storage

from .core import Config, Rag


def demo_config():
    demo_config = Config()
    demo_config.register_component(source_storage.RagnaDemoSourceStorage)
    demo_config.register_component(assistant.RagnaDemoAssistant)
    return demo_config


demo_config = demo_config()


# def builtin_config():
#     from ragna.core import Assistant, SourceStorage
#
#     builtin_config = Config()
#     builtin_config.state_database_url = (
#         f"sqlite:///{builtin_config.local_cache_root}/ragna.db"
#     )
#     builtin_config.queue_database_url = str(builtin_config.local_cache_root / "queue")
#
#     for module, cls in [(source_storage, SourceStorage), (assistant, Assistant)]:
#         for obj in module.__dict__.values():
#             if isinstance(obj, type) and issubclass(obj, cls) and obj.is_available():
#                 builtin_config.register_component(obj)
#
#     return builtin_config
#
#
# builtin_config = builtin_config()
