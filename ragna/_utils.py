from __future__ import annotations

import contextlib
import functools
import getpass
import inspect
import os
import shlex
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Iterator,
    Optional,
    TypeVar,
    Union,
    cast,
)

from starlette.concurrency import iterate_in_threadpool, run_in_threadpool

T = TypeVar("T")

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
        Ragna's local root directory.
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


def as_awaitable(
    fn: Union[Callable[..., T], Callable[..., Awaitable[T]]], *args: Any, **kwargs: Any
) -> Awaitable[T]:
    if inspect.iscoroutinefunction(fn):
        fn = cast(Callable[..., Awaitable[T]], fn)
        awaitable = fn(*args, **kwargs)
    else:
        fn = cast(Callable[..., T], fn)
        awaitable = run_in_threadpool(fn, *args, **kwargs)

    return awaitable


def as_async_iterator(
    fn: Union[Callable[..., Iterator[T]], Callable[..., AsyncIterator[T]]],
    *args: Any,
    **kwargs: Any,
) -> AsyncIterator[T]:
    if inspect.isasyncgenfunction(fn):
        fn = cast(Callable[..., AsyncIterator[T]], fn)
        async_iterator = fn(*args, **kwargs)
    else:
        fn = cast(Callable[..., Iterator[T]], fn)
        async_iterator = iterate_in_threadpool(fn(*args, **kwargs))

    return async_iterator


def default_user() -> str:
    with contextlib.suppress(Exception):
        return getpass.getuser()
    with contextlib.suppress(Exception):
        return os.getlogin()
    return "Bodil"


class BackgroundSubprocess:
    def __init__(
        self,
        *cmd: str,
        stdout: Any = sys.stdout,
        stderr: Any = sys.stdout,
        startup_fn: Optional[Callable[[], bool]] = None,
        startup_timeout: float = 10,
        terminate_timeout: float = 10,
        text: bool = True,
        **subprocess_kwargs: Any,
    ) -> None:
        self._terminate_timeout = terminate_timeout

        self._process = subprocess.Popen(
            cmd, stdout=stdout, stderr=stderr, text=text, **subprocess_kwargs
        )
        try:
            if startup_fn:

                @timeout_after(startup_timeout, message=shlex.join(cmd))
                def wait() -> None:
                    while not startup_fn():
                        time.sleep(0.2)

                wait()
        except Exception:
            self.terminate()
            raise

    def terminate(self) -> tuple[str | bytes, str | bytes]:
        @timeout_after(self._terminate_timeout)
        def terminate() -> tuple[str | bytes, str | bytes]:
            self._process.terminate()
            return self._process.communicate()

        try:
            return terminate()  # type: ignore[no-any-return]
        except TimeoutError:
            self._process.kill()
            return self._process.communicate()

    def __enter__(self) -> BackgroundSubprocess:
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.terminate()
