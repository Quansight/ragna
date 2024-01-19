from pathlib import Path
from types import SimpleNamespace
from typing import cast

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

import ragna
from ragna.core import RagnaException

from . import _api as api
from . import _auth
from . import _ui as ui
from ._engine import Engine
from ._session import SessionMiddleware
from ._utils import redirect_response


def make_app(config):
    # FIXME: remove the optional deploy_ui
    app = FastAPI(title="Ragna", version=ragna.__version__)

    # from config
    config = SimpleNamespace(
        authentication=_auth.NoAuth,
        deploy=SimpleNamespace(
            session_storage_url="",
            token_expires=3600,
            cookie_expires=3600,
        ),
    )

    @app.exception_handler(RagnaException)
    async def ragna_exception_handler(
        request: Request, exc: RagnaException
    ) -> JSONResponse:
        if exc.http_detail is RagnaException.EVENT:
            detail = exc.event
        elif exc.http_detail is RagnaException.MESSAGE:
            detail = str(exc)
        else:
            detail = cast(str, exc.http_detail)
        return JSONResponse(
            status_code=exc.http_status_code,
            content={"error": {"message": detail}},
        )

    app.add_middleware(SessionMiddleware, config=config)
    app.add_middleware(
        CORSMiddleware,
        # FIXME
        allow_origins="http://localhost:31476",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    engine = Engine(config)
    app.include_router(
        ui.make_router(engine, config), prefix="/ui", include_in_schema=False
    )
    app.include_router(api.make_router(engine, config), prefix="/api")

    app.mount(
        "/static",
        StaticFiles(directory=Path(__file__).parent / "static"),
        name="static",
    )

    @app.get("/", include_in_schema=False)
    async def ui_redirect(request: Request) -> Response:
        return redirect_response("/ui", htmx=request)

    @app.get("/version")
    async def version():
        return ragna.__version__

    @app.get("/health")
    async def health():
        return Response(b"", status_code=status.HTTP_200_OK)

    return app
