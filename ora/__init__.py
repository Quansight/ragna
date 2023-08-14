try:
    from ._version import __version__
except ModuleNotFoundError:
    import warnings

    warnings.warn("ora was not properly installed!")
    del warnings

    __version__ = "UNKNOWN"

from . import extensions
