from typing import Union

from fastapi import Request
from fastapi.responses import RedirectResponse, Response


def redirect_response(
    url, *, htmx: Union[bool, Request] = True, status_code: int = 307
) -> Response:
    if isinstance(htmx, Request):
        htmx = htmx.headers.get("HX-Request") == "true"

    if htmx:
        return Response(b"", headers={"HX-Redirect": url}, status_code=status_code)
    else:
        return RedirectResponse(url, status_code=status_code)
