try:
    from ._version import __version__
except ModuleNotFoundError:
    import warnings

    warnings.warn("ragna was not properly installed!")
    del warnings

    __version__ = "UNKNOWN"

from . import core, llm, source_storage

from .core import Config, Rag

demo_config = Config()
demo_config.register_component(source_storage.RagnaDemoSourceStorage)
demo_config.register_component(llm.RagnaDemoLlm)
