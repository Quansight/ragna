from pathlib import Path
from types import SimpleNamespace
from typing import cast

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, RedirectResponse
from fastapi.staticfiles import StaticFiles


import ragna
from ragna.core import RagnaException

from . import _api as api
from . import _auth
from . import _ui as ui
from ._session import SessionMiddleware

# # from config
# config = SimpleNamespace(
#     authentication=_auth.DummyBasicAuth,
#     deploy=SimpleNamespace(
#         session_storage_url="",
#         database_url="memory",
#         token_expires=3600,
#         cookie_expires=3600,
#     ),
# )


def make_app(*, config, deploy_api: bool, deploy_ui: bool):
    app = FastAPI(title="Ragna", version=ragna.__version__)

    database = None

    app.add_middleware(
        SessionMiddleware,
        config=config,
        database=database,
        api=deploy_api,
        ui=deploy_ui,
    )
    app.add_middleware(
        CORSMiddleware,
        # FIXME
        allow_origins="http://localhost:31476",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if deploy_api:
        app.include_router(api.make_router(config, database), prefix="/api")

    if deploy_ui:

        @app.get("/ui")
        async def bkapp_page(request: Request):
            script = server_document("http://127.0.0.1:31477")
            return templates.TemplateResponse(
                "base.html", {"request": request, "script": script}
            )

        ui_app(
            config=Config(
                api=dict(origins=["http://localhost:8000"]),
                ui=dict(origins=["http://localhost:8000"]),
            ),
            open_browser=False,
        ).serve()

    @app.get("", include_in_schema=False)
    async def base_redirect() -> Response:
        return RedirectResponse(
            "/ui" if deploy_ui else "/api/docs", status_code=status.HTTP_303_SEE_OTHER
        )

    @app.get("/version")
    async def version():
        return ragna.__version__

    @app.get("/health")
    async def health():
        return Response(b"", status_code=status.HTTP_200_OK)

    auth = config.authentication()

    @app.get("/login")
    async def login_page(request: Request):
        return await as_awaitable(auth.login_page, request)

    async def _login(request: Request):
        result = await as_awaitable(auth.login, request)
        if not isinstance(result, User):
            return result

        request.state.session = Session(id=request.state.session_id, user=result)
        return RedirectResponse(
            "/ui" if deploy_ui else "/api/docs", status_code=status.HTTP_303_SEE_OTHER
        )

    @app.post("/login")
    async def login(request: Request):
        return await _login(request)

    @app.get("/oauth-callback")
    async def oauth_callback(request: Request):
        return await _login(request)

    @app.post("/logout")
    async def logout():
        return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)

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
