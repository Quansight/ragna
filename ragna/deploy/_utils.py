from typing import Optional

from fastapi import status
from fastapi.responses import RedirectResponse

from ragna.core import RagnaException

_REDIRECT_ROOT_PATH: Optional[str] = None


def set_redirect_root_path(root_path: str):
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
