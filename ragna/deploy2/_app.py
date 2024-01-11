from pathlib import Path
from typing import cast

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

import ragna
from ragna.core import RagnaException

from . import _api as api
from . import _session as session
from . import _ui as ui


def app(config):
    app = FastAPI(title="Ragna", version=ragna.__version__)

    app.include_router(api.router, prefix="/api")
    app.include_router(ui.router, prefix="/ui", include_in_schema=False)

    @app.get("/")
    async def ui_redirect() -> RedirectResponse:
        return RedirectResponse("/ui")

    # TODO: Preferrably, this would be mounted from the UI router. Unfortunately, this
    #  is currently not possible. See https://github.com/tiangolo/fastapi/issues/10180
    app.mount(
        "/static",
        StaticFiles(directory=Path(__file__).parent / "static"),
        name="static",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=handle_localhost_origins(config.api.origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(session.Middleware)

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

    return app
