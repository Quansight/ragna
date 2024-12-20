import contextlib
import threading
import time
import uuid
import webbrowser
from pathlib import Path
from typing import AsyncContextManager, AsyncIterator, Callable, Optional, cast

import httpx
import panel.io.fastapi
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

import ragna
from ragna.core import RagnaException

from . import _schemas as schemas
from ._api import make_router as make_api_router
from ._auth import UserDependency
from ._config import Config
from ._engine import Engine
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
    set_redirect_root_path(config.root_path)

    lifespan: Optional[Callable[[FastAPI], AsyncContextManager]]
    if open_browser:

        @contextlib.asynccontextmanager
        async def lifespan(app: FastAPI) -> AsyncIterator[None]:
            try:
                browser = webbrowser.get()
            except webbrowser.Error as error:
                print(str(error))
                yield
                return

            def target() -> None:
                url = f"http://{config.hostname}:{config.port}"
                client = httpx.Client(base_url=url)

                def server_available() -> bool:
                    try:
                        return client.get("/health").is_success
                    except httpx.ConnectError:
                        return False

                while not server_available():
                    time.sleep(0.1)

                browser.open(url)

            # We are starting the browser on a thread, because the server can only
            # become available _after_ the yield below. By setting daemon=True, the
            # thread will automatically terminated together with the main thread. This
            # is only relevant when the server never becomes available, e.g. if an error
            # occurs. In this case our thread would be stuck in an endless loop.
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

    engine = Engine(
        config=config,
        ignore_unavailable_components=ignore_unavailable_components,
    )

    config.auth._add_to_app(app, config=config, engine=engine, api=api, ui=ui)

    if api:
        app.include_router(make_api_router(engine), prefix="/api")

    if ui:
        ui_app = make_ui_app(engine)
        panel.io.fastapi.add_applications({"/ui": ui_app.index_page}, app=app)
        for dir in ["css", "imgs"]:
            app.mount(
                f"/{dir}",
                StaticFiles(directory=str(Path(__file__).parent / "_ui" / dir)),
                name=dir,
            )

    @app.get("/", include_in_schema=False)
    async def base_redirect() -> Response:
        return redirect("/ui" if ui else "/docs")

    @app.get("/health")
    async def health() -> Response:
        return Response(b"", status_code=status.HTTP_200_OK)

    @app.get("/version")
    async def version() -> str:
        return ragna.__version__

    @app.get("/user")
    async def user(user: UserDependency) -> schemas.User:
        return user

    @app.get("/api-keys")
    def list_api_keys(user: UserDependency) -> list[schemas.ApiKey]:
        return engine.list_api_keys(user=user.name)

    @app.post("/api-keys")
    def create_api_key(
        user: UserDependency, api_key_creation: schemas.ApiKeyCreation
    ) -> schemas.ApiKey:
        return engine.create_api_key(user=user.name, api_key_creation=api_key_creation)

    @app.delete("/api-keys/{id}")
    def delete_api_key(user: UserDependency, id: uuid.UUID) -> None:
        return engine.delete_api_key(user=user.name, id=id)

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
