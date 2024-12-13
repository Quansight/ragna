from typing import Optional
from urllib.parse import SplitResult, urlsplit, urlunsplit

from fastapi import status
from fastapi.responses import RedirectResponse

from ragna.core import RagnaException

_REDIRECT_ROOT_PATH: Optional[str] = None


def set_redirect_root_path(root_path: str) -> None:
    global _REDIRECT_ROOT_PATH
    _REDIRECT_ROOT_PATH = root_path


def redirect(
    url: str, *, status_code: int = status.HTTP_303_SEE_OTHER
) -> RedirectResponse:
    if _REDIRECT_ROOT_PATH is None:
        raise RagnaException

    if url.startswith("/"):
        url = _REDIRECT_ROOT_PATH + url

    return RedirectResponse(url, status_code=status_code)


def handle_localhost_origins(origins: list[str]) -> list[str]:
    # Since localhost is an alias for 127.0.0.1, we allow both so users and developers
    # don't need to worry about it.
    localhost_origins = {
        components.hostname: components
        for url in origins
        if (components := urlsplit(url)).hostname in {"127.0.0.1", "localhost"}
    }
    if "127.0.0.1" in localhost_origins and "localhost" not in localhost_origins:
        origins.append(
            urlunsplit(_replace_hostname(localhost_origins["127.0.0.1"], "localhost"))
        )
    elif "localhost" in localhost_origins and "127.0.0.1" not in localhost_origins:
        origins.append(
            urlunsplit(_replace_hostname(localhost_origins["localhost"], "127.0.0.1"))
        )

    return origins


def _replace_hostname(split_result: SplitResult, hostname: str) -> SplitResult:
    # This is a separate function, since hostname is not an element of the SplitResult
    # namedtuple, but only a property. Thus, we need to replace the netloc item, from
    # which the hostname is generated.
    if split_result.port is None:
        netloc = hostname
    else:
        netloc = f"{hostname}:{split_result.port}"
    return split_result._replace(netloc=netloc)
