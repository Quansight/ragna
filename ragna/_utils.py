import functools
import inspect
import os
import sys
import threading
from pathlib import Path
from typing import Any, Callable, Optional, Union
from urllib.parse import SplitResult, urlsplit, urlunsplit

_LOCAL_ROOT = (
    Path(os.environ.get("RAGNA_LOCAL_ROOT", "~/.cache/ragna")).expanduser().resolve()
)


def make_directory(path: Union[str, Path]) -> Path:
    path = Path(path).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def local_root(path: Optional[Union[str, Path]] = None) -> Path:
    """Get or set the local root directory Ragna uses for storing files.

    Defaults to the value of the `RAGNA_LOCAL_ROOT` environment variable or otherwise to
    `~/.cache/ragna`.

    Args:
        path: If passed, this is set as new local root directory.

    Returns:
        Ragnas local root directory.
    """
    global _LOCAL_ROOT
    if path is not None:
        _LOCAL_ROOT = make_directory(path)

    return _LOCAL_ROOT


def fix_module(globals: dict[str, Any]) -> None:
    """Fix the __module__ attribute on public objects to hide internal structure.

    Put the following snippet at the end of public `__init__.py` files of ragna
    subpackages. This will hide any internally private structure.

    ```python
    # isort: split

    from ragna._utils import fix_module

    fix_module(globals())
    del fix_module
    ```
    """
    for name, obj in globals.items():
        if name.startswith("_"):
            continue

        obj.__module__ = globals["__package__"]


def _replace_hostname(split_result: SplitResult, hostname: str) -> SplitResult:
    # This is a separate function, since hostname is not an element of the SplitResult
    # namedtuple, but only a property. Thus, we need to replace the netloc item, from
    # which the hostname is generated.
    if split_result.port is None:
        netloc = hostname
    else:
        netloc = f"{hostname}:{split_result.port}"
    return split_result._replace(netloc=netloc)


def handle_localhost_origins(origins: list[str]) -> list[str]:
    # Since localhost is an alias for 127.0.0.1, we allow both so users and developers
    # don't need to worry about it.
    localhost_origins = {
        components.hostname: components
        for url in origins
        if (components := urlsplit(url)).hostname in {"127.0.0.1", "localhost"}
    }
    if "127.0.0.1" in localhost_origins:
        origins.append(
            urlunsplit(_replace_hostname(localhost_origins["127.0.0.1"], "localhost"))
        )
    elif "localhost" in localhost_origins:
        origins.append(
            urlunsplit(_replace_hostname(localhost_origins["localhost"], "127.0.0.1"))
        )

    return origins


def timeout_after(
    seconds: float = 30, *, message: str = ""
) -> Callable[[Callable], Callable]:
    timeout = f"Timeout after {seconds:.1f} seconds"
    message = f"{timeout}: {message}" if message else timeout

    def decorator(fn: Callable) -> Callable:
        if is_debugging():
            return fn

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result: Any = TimeoutError(message)

            def target() -> None:
                nonlocal result
                try:
                    result = fn(*args, **kwargs)
                except Exception as exc:
                    result = exc

            thread = threading.Thread(target=target)
            thread.daemon = True

            thread.start()
            thread.join(seconds)

            if isinstance(result, Exception):
                raise result

            return result

        return wrapper

    return decorator


# Vendored from pytest-timeout
# https://github.com/pytest-dev/pytest-timeout/blob/d91e6d8d69ad706e38a2c9de461a72c4d19777ff/pytest_timeout.py#L218-L247
def is_debugging() -> bool:
    trace_func = sys.gettrace()
    trace_module = None
    if trace_func:
        trace_module = inspect.getmodule(trace_func) or inspect.getmodule(
            trace_func.__class__
        )
    if trace_module:
        parts = trace_module.__name__.split(".")
        for name in {"pydevd", "bdb", "pydevd_frame_evaluator"}:
            if any(part.startswith(name) for part in parts):
                return True
    return False
