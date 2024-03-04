try:
    from ._version import __version__
except ModuleNotFoundError:
    import warnings

    warnings.warn("ragna was not properly installed!")
    del warnings

    __version__ = "UNKNOWN"

from ._utils import local_root

# isort: split

from . import assistants, core, deploy, source_storages
from .core import Rag

__all__ = [
    "__version__",
    "Rag",
    "assistants",
    "core",
    "deploy",
    "local_root",
    "source_storages",
]
