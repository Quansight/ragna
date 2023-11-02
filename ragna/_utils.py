import functools
import threading
from typing import Any, Callable
from urllib.parse import SplitResult, urlsplit, urlunsplit


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
    seconds: float = 5, *, message: str = ""
) -> Callable[[Callable], Callable]:
    timeout = f"Timeout after {seconds:.1f} seconds"
    message = timeout if message else f"{timeout}: {message}"

    def decorator(fn: Callable) -> Callable:
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
