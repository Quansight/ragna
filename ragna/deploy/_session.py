import uuid
from typing import Annotated

from fastapi import Depends, Request, status
from fastapi.responses import Response
from fastapi.security.utils import get_authorization_scheme_param
from starlette.middleware.base import BaseHTTPMiddleware

from ._utils import redirect
from .schemas import Session


class SessionMiddleware(BaseHTTPMiddleware):
    _COOKIE_NAME = "Ragna"

    def __init__(self, app, *, config, database, api: bool, ui: bool):
        super().__init__(app)
        self._config = config
        self._database = database
        self._api = api
        self._ui = ui
        self._sessions: dict[str, Session] = {}

    async def dispatch(self, request: Request, call_next) -> Response:
        # call_next_orig = call_next
        #
        # async def call_next(request):
        #     response = await call_next_orig(request)
        #     print(f"{request.method=} {request.url.path=} {response.headers}")
        #     return response

        if (authorization := request.headers.get("Authorization")) is not None:
            return await self._authorization_dispatch(
                request, call_next, authorization=authorization
            )
        elif (cookie := request.cookies.get(self._COOKIE_NAME)) is not None:
            return await self._cookie_dispatch(request, call_next, cookie=cookie)
        elif request.url.path in {"/login", "/oauth-callback"}:
            return await self._login_dispatch(request, call_next)
        elif self._api and request.url.path.startswith("/api"):
            return self._unauthorized()
        elif self._ui and request.url.path.startswith("/ui"):
            return redirect("/login")
        else:
            # Either an unknown route or something on the default router. In any case,
            # this doesn't need a session and so we let it pass.
            request.state.session = None
            return await call_next(request)

    async def _cookie_dispatch(self, request, call_next, *, cookie) -> Response:
        session = self._sessions.get(cookie)
        if session is not None and request.url.path == "/logout":
            del self._sessions[cookie]
            session = None
        if session is None:
            response = redirect("/login")
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
            session = self._sessions[token] = Session(user=user)

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

    def _unauthorized(self) -> Response:
        return Response(
            content="Not authenticated",
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )

    def _add_cookie(self, response: Response, cookie: str) -> None:
        response.set_cookie(
            key=self._COOKIE_NAME,
            value=cookie,
            # FIXME
            max_age=3600,
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


async def _get_session(request: Request) -> Session:
    return request.state.session


SessionDependency = Annotated[Session, Depends(_get_session)]


async def _get_user(session: SessionDependency):
    return session.user


UserDependency = Annotated[str, Depends(_get_user)]
