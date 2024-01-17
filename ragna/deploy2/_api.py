from fastapi import APIRouter, Request, Response

from ._utils import redirect_response


def make_router(config):
    router = APIRouter()

    @router.get("/", include_in_schema=False)
    async def ui_redirect(request: Request) -> Response:
        return redirect_response("/docs", htmx=request)

    return router
