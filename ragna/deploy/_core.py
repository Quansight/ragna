from typing import cast

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response


import ragna
from ragna.core import RagnaException

from ._api import make_router as make_api_router
from ._ui import app as make_ui_app
from ._config import Config
from ._utils import redirect, set_redirect_root_path, handle_localhost_origins


def make_app(
    config: Config,
    *,
    api: bool,
    ui: bool,
    ignore_unavailable_components: bool,
) -> FastAPI:
    ragna.local_root(config.local_root)
    set_redirect_root_path(config.root_path)

    app = FastAPI(title="Ragna", version=ragna.__version__)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=handle_localhost_origins(config.origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if api:
        app.include_router(
            make_api_router(
                config,
                ignore_unavailable_components=ignore_unavailable_components,
            ),
            prefix="/api",
        )

    if ui:
        panel_app = make_ui_app(config=config)
        panel_app.serve_with_fastapi(app, endpoint="/ui")

    @app.get("/", include_in_schema=False)
    async def base_redirect() -> Response:
        return redirect("/ui" if ui else "/docs")

    @app.get("/health")
    async def health() -> Response:
        return Response(b"", status_code=status.HTTP_200_OK)

    @app.get("/version")
    async def version() -> str:
        return ragna.__version__

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
