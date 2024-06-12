import contextlib
import threading
import time
import webbrowser
from typing import AsyncContextManager, AsyncIterator, Callable, Optional, cast

import httpx
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

import ragna
from ragna.core import RagnaException

from ._api import make_router as make_api_router
from ._config import Config
from ._ui import app as make_ui_app
from ._utils import handle_localhost_origins, redirect, set_redirect_root_path


def make_app(
    config: Config,
    *,
    api: bool,
    ui: bool,
    ignore_unavailable_components: bool,
    open_browser: bool,
) -> FastAPI:
    ragna.local_root(config.local_root)
    set_redirect_root_path(config.root_path)

    lifespan: Optional[Callable[[FastAPI], AsyncContextManager]]
    if open_browser:

        @contextlib.asynccontextmanager
        async def lifespan(app: FastAPI) -> AsyncIterator[None]:
            # We are starting the browser on a thread, because the server is only
            # accessible _after_ the yield below.
            def target() -> None:
                client = httpx.Client(base_url=config._url)

                def server_available():
                    try:
                        return client.get("/health").is_success
                    except httpx.ConnectError:
                        return False

                while not server_available():
                    time.sleep(0.1)

                webbrowser.open(config._url)

            # By setting daemon=True, the thread will automatically terminated when the
            # main thread is terminated. This is only relevant when the server never
            # becomes available. In this case our thread would be stuck in an endless
            # loop.
            thread = threading.Thread(target=target, daemon=True)
            thread.start()
            yield

    else:
        lifespan = None

    app = FastAPI(title="Ragna", version=ragna.__version__, lifespan=lifespan)

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
