import panel as pn
from bokeh.embed import server_document
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.middleware import Middleware

from ragna.deploy._ui import app as ui_app
from ragna.deploy import Config

from functools import partial
import abc
import os
import secrets
import time
import uuid
from typing import Annotated, Awaitable, Callable, Optional, cast

import jwt
import pydantic
from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import Response, HTMLResponse
from fastapi.security.utils import get_authorization_scheme_param
from starlette.middleware.base import BaseHTTPMiddleware

from fastapi.responses import RedirectResponse, Response


class SessionMiddleware(BaseHTTPMiddleware):
    _COOKIE_NAME = "Ragna"

    def __init__(self, app, *, config, database):
        super().__init__(app)
        self._config = config
        self._database = database
        self._sessions: dict[str, Session] = {}

    async def dispatch(self, request: Request, call_next) -> Response:
        if (cookie := request.cookies.get(self._COOKIE_NAME)) is not None:
            return await self._cookie_dispatch(request, call_next, cookie=cookie)
        elif (authorization := request.headers.get("Authorization")) is not None:
            return await self._authorization_dispatch(
                request, call_next, authorization=authorization
            )
        elif request.url.path in {"/login", "/oauth-callback"}:
            return await self._login_dispatch(request, call_next)
        elif request.url.path.startswith("/ui"):
            return self._login_redirect()
        elif request.url.path.startswith("/api"):
            return self._unauthorized()
        else:
            # Either an unknown route or something on the default router. In any case,
            # this doesn't need a session and so we let it pass.
            return await call_next(request)

    async def _cookie_dispatch(self, request, call_next, *, cookie) -> Response:
        session = self._sessions.get(cookie)
        if session is not None and request.url.path == "/logout":
            del self._sessions[cookie]
            session = None
        if session is None:
            response = self._login_redirect()
            self._delete_cookie(response)
            return response

        request.state.session = session
        response = await call_next(request)
        self._add_cookie(response, cookie)
        return response

    async def _authorization_dispatch(
        self, request, call_next, authorization
    ) -> Response:
        scheme, token = get_authorization_scheme_param(authorization)
        if scheme.lower() != "bearer":
            return self._unauthorized()

        session = self._sessions.get(token)
        user = self._database.get_user_by_token(token)
        if session is None and user is None:
            return self._unauthorized()
        elif session is not None and token != user.token:
            del self._sessions[token]
            return self._unauthorized()
        elif session is None:
            # First time the API token is used
            session = self._sessions[token] = Session(user)

        request.state.session = session
        return await call_next(request)

    async def _login_dispatch(self, request, call_next) -> Response:
        request.state.session = None
        response = await call_next(request)
        session = request.state.session

        if session is not None:
            cookie = str(uuid.uuid4())
            self._sessions[cookie] = session
            self._add_cookie(response, cookie=cookie)

        return response

    def _login_redirect(self) -> RedirectResponse:
        return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)

    def _unauthorized(self) -> Response:
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    def _add_cookie(self, response: Response, cookie: str) -> None:
        response.set_cookie(
            key=self._COOKIE_NAME,
            value=cookie,
            # max_age=self._config.deploy.cookie_expires,
            httponly=True,
            samesite="lax",
        )

    def _delete_cookie(self, response: Response) -> None:
        response.delete_cookie(
            key=self._COOKIE_NAME,
            httponly=True,
            samesite="lax",
        )


app = FastAPI()
templates = Jinja2Templates(directory="./templates")
app.add_middleware(SessionMiddleware)


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


@app.get("/login")
async def login():
    return "hello"
