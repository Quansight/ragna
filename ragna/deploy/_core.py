from pathlib import Path
from typing import cast

from bokeh.embed import server_document
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

import ragna
from ragna._utils import as_awaitable
from ragna.core import RagnaException

from . import _templates as templates
from . import schemas as schemas
from ._api import make_router as make_api_router
from ._config import Config
from ._database import Database
from ._session import SessionMiddleware, UserDependency
from ._ui import app as make_ui_app


def make_app(
    config: Config,
    *,
    api: bool,
    ui: bool,
    ignore_unavailable_components: bool,
) -> FastAPI:
    app = FastAPI(title="Ragna", version=ragna.__version__)

    database = Database(config)

    app.mount(
        "/static",
        StaticFiles(directory=Path(__file__).parent / "_static"),
        name="static",
    )

    app.add_middleware(
        SessionMiddleware,
        config=config,
        database=database,
        api=api,
        ui=ui,
    )
    app.add_middleware(
        CORSMiddleware,
        # FIXME
        allow_origins=[
            "http://localhost:31476",
            # "http://localhost:31477",
            # "http://127.0.0.1:31477",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    add_auth(app, config)

    if api:
        app.include_router(
            make_api_router(
                config,
                database,
                ignore_unavailable_components=ignore_unavailable_components,
            ),
            prefix="/api",
        )

    if ui:
        # FIXME: find a way to open the browser
        make_ui_app(config=config, open_browser=False).serve()

        @app.get("/ui", include_in_schema=False)
        async def ui_(request: Request):
            return HTMLResponse(
                templates.render(
                    "ui.html",
                    script=server_document(
                        # FIXME: from config
                        "http://127.0.0.1:31477",
                        # Unfortunately, we currently need to rely on this non-standard
                        # way of forwarding the cookies to the UI. See
                        # https://github.com/bokeh/bokeh/issues/13792 for details.
                        headers={"X-Cookie": request.headers["Cookie"]},
                    ),
                )
            )

    @app.get("/", include_in_schema=False)
    async def base_redirect(request: Request) -> Response:
        return RedirectResponse(
            "/ui" if ui else "/docs", status_code=status.HTTP_303_SEE_OTHER
        )

    @app.get("/version")
    async def version():
        return ragna.__version__

    @app.get("/user")
    async def user(user: UserDependency):
        return user

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


def add_auth(app: FastAPI, config: Config) -> None:
    auth = config.auth()

    @app.get("/login", include_in_schema=False)
    async def login_page(request: Request):
        return await as_awaitable(auth.login_page, request)

    async def _login(request: Request):
        result = await as_awaitable(auth.login, request)
        if not isinstance(result, schemas.User):
            return result

        request.state.session = schemas.Session(user=result)
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)

    @app.post("/login", include_in_schema=False)
    async def login(request: Request):
        return await _login(request)

    @app.get("/oauth-callback", include_in_schema=False)
    async def oauth_callback(request: Request):
        return await _login(request)

    @app.post("/logout", include_in_schema=False)
    async def logout():
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
