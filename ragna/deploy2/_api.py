from fastapi import APIRouter, Request, Response

from . import schemas
from ._utils import redirect_response


def make_router(engine, config):
    router = APIRouter()

    @router.get("/", include_in_schema=False)
    async def docs_redirect(request: Request) -> Response:
        return redirect_response("/docs", htmx=request)

    @router.get("/chats")
    def get_chats() -> list[schemas.Chat]:
        pass

    return router
