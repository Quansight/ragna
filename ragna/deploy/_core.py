import contextlib
from pathlib import Path
from typing import AsyncContextManager, Optional, cast

from bokeh.embed import server_document
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
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
from ._utils import redirect, set_redirect_root_path


def make_app(
    config: Config,
    *,
    api: bool,
    ui: bool,
    ignore_unavailable_components: bool,
) -> FastAPI:
    ragna.local_root(config.local_root)
    set_redirect_root_path(config.api.root_path)

    lifespan: Optional[AsyncContextManager]
    if ui:

        @contextlib.asynccontextmanager
        async def lifespan(app):
            # FIXME threaded and start here? YES!!
            server = make_ui_app(config=config, open_browser=False).serve()
            try:
                yield
            finally:
                server.stop()

    else:
        lifespan = None

    app = FastAPI(title="Ragna", version=ragna.__version__, lifespan=lifespan)

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
        # FIXME from config
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
    # https://nebari.quansight.dev/user/pmeier@quansight.com/proxy/31476/

    if ui:

        @app.get("/ui", include_in_schema=False)
        async def ui_(request: Request):
            return HTMLResponse(
                templates.render(
                    "ui.html",
                    script=server_document(
                        f"http://{config.ui.hostname}:{config.ui.port}",
                        # Unfortunately, we currently need to rely on this non-standard
                        # way of forwarding the cookies to the UI. See
                        # https://github.com/bokeh/bokeh/issues/13792 for details.
                        # TODO: When https://github.com/bokeh/bokeh/pull/13800 is
                        #  released, we need to remove the headers and instead pass
                        #  with_credentials=True. Plus we also need to fix the UI to
                        #  just use the standard cookies instead of parsing this header.
                        headers={"X-Cookie": request.headers["Cookie"]},
                    ),
                )
            )

    @app.get("/", include_in_schema=False)
    async def base_redirect() -> Response:
        return redirect("/ui" if ui else "/docs")

    @app.get("/health")
    async def health():
        return Response(b"", status_code=status.HTTP_200_OK)

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
        return redirect("/")

    @app.post("/login", include_in_schema=False)
    async def login(request: Request):
        return await _login(request)

    @app.get("/oauth-callback", include_in_schema=False)
    async def oauth_callback(request: Request):
        return await _login(request)

    @app.post("/logout", include_in_schema=False)
    async def logout():
        return redirect("/")
