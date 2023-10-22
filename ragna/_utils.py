import functools
import threading
from typing import Any
from urllib.parse import SplitResult, urlsplit, urlunsplit


def fix_module(globals: dict[str, Any]) -> None:
    """Fix the __module__ attribute on public objects to hide internal structure.

    Put the following snippet at the end of public `__init__.py` files of ragna
    subpackages. This will hide any internally private structure.

    ```python
    from ragna._utils import fix_module  # usort: skip

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


def get_origins(url: str) -> list[str]:
    origins = [url]

    # Since localhost is an alias for 127.0.0.1, we allow both so users and developers
    # don't need to worry about it.
    components = urlsplit(url)
    if components.hostname == "127.0.0.1":
        origins.append(urlunsplit(_replace_hostname(components, "localhost")))
    elif components.hostname == "localhost":
        origins.append(urlunsplit(_replace_hostname(components, "127.0.0.1")))

    return origins


def timeout_after(seconds=5, *, message=None):
    timeout = f"Timeout after {seconds:.1f} seconds"
    message = timeout if message is None else f"{timeout}: {message}"

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            result = TimeoutError(message)

            def target():
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
