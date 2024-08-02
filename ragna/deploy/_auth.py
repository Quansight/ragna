import abc
import base64
import json
import os
import uuid
from typing import Annotated, Awaitable, Callable, Optional, Union, cast

import httpx
import pydantic
from fastapi import Depends, FastAPI, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.security.utils import get_authorization_scheme_param
from starlette.middleware.base import BaseHTTPMiddleware
from tornado.web import create_signed_value

from ragna._utils import as_awaitable, default_user
from ragna.core import RagnaException

from . import _schemas as schemas
from . import _templates as templates
from ._config import Config
from ._engine import Engine
from ._key_value_store import KeyValueStore
from ._utils import redirect


class Session(pydantic.BaseModel):
    user: schemas.User


CallNext = Callable[[Request], Awaitable[Response]]


class SessionMiddleware(BaseHTTPMiddleware):
    def __init__(
        self, app: FastAPI, *, config: Config, engine: Engine, api: bool, ui: bool
    ) -> None:
        super().__init__(app)
        self._config = config
        self._engine = engine
        self._api = api
        self._ui = ui
        self._sessions: KeyValueStore[Session] = config.key_value_store()

    _COOKIE_NAME = "ragna"

    async def dispatch(self, request: Request, call_next: CallNext) -> Response:
        if (authorization := request.headers.get("Authorization")) is not None:
            return await self._api_token_dispatch(
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

    async def _api_token_dispatch(
        self, request: Request, call_next: CallNext, authorization: str
    ) -> Response:
        scheme, api_key = get_authorization_scheme_param(authorization)
        if scheme.lower() != "bearer":
            return self._unauthorized()

        user = self._engine.get_user(api_key=api_key)
        if user is None:
            # Unknown API key
            return self._unauthorized()

        session = self._sessions.get(api_key)
        if session is None:
            # First time the API key is used
            session = self._sessions[api_key] = Session(user=user)

        request.state.session = session
        return await call_next(request)

    # panel uses cookies to transfer user information (see _cookie_dispatch() below) and
    # signs them for security. However, since this happens after our authentication
    # check, we can use an arbitrary, hardcoded value here.
    PANEL_COOKIE_SECRET = "ragna"

    async def _cookie_dispatch(
        self, request: Request, call_next: CallNext, *, cookie: str
    ) -> Response:
        session = self._sessions.get(cookie)
        response: Response
        if session is None:
            # Invalid cookie
            response = redirect("/login")
            self._delete_cookie(response)
            return response

        request.state.session = session
        if self._ui and request.method == "GET" and request.url.path == "/ui":
            # panel.state.user and panel.state.user_info are based on the two cookies
            # below that the panel auth flow sets. Since we don't want extra cookies
            # just for panel, we just inject them into the scope here, which will be
            # parsed by panel down the line. After this initial request, the values are
            # tied to the active session and don't have to be set again.
            extra_cookies = {
                "user": session.user.name,
                "id_token": base64.b64encode(json.dumps(session.user.data).encode()),
            }
            extra_values = [
                (
                    f"{key}=".encode()
                    + create_signed_value(
                        self.PANEL_COOKIE_SECRET, key, value, version=1
                    )
                )
                for key, value in extra_cookies.items()
            ]

            cookie_key = b"cookie"
            idx, value = next(
                (idx, value)
                for idx, (key, value) in enumerate(request.scope["headers"])
                if key == cookie_key
            )
            # We are not setting request.cookies or request.headers here, because any
            # changes to them are not reflected back to the scope, which is the only
            # safe way to transfer data between the middleware and an endpoint.
            request.scope["headers"][idx] = (
                cookie_key,
                b";".join([value, *extra_values]),
            )

        response = await call_next(request)

        if request.url.path == "/logout":
            del self._sessions[cookie]
            self._delete_cookie(response)
        else:
            self._add_cookie(response, cookie)

        return response

    async def _login_dispatch(self, request: Request, call_next: CallNext) -> Response:
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
    session = cast(Optional[Session], request.state.session)
    if session is None:
        raise RagnaException("ADDME")
    return session


SessionDependency = Annotated[Session, Depends(_get_session)]


async def _get_user(session: SessionDependency) -> schemas.User:
    return session.user


UserDependency = Annotated[schemas.User, Depends(_get_user)]


class Auth(abc.ABC):
    @classmethod
    def _add_to_app(
        cls, app: FastAPI, *, config: Config, engine: Engine, api: bool, ui: bool
    ) -> None:
        self = cls()

        @app.get("/login", include_in_schema=False)
        async def login_page(request: Request) -> Response:
            return await as_awaitable(self.login_page, request)

        async def _login(request: Request) -> Response:
            result = await as_awaitable(self.login, request)
            if not isinstance(result, schemas.User):
                return result

            engine.maybe_add_user(result)
            request.state.session = Session(user=result)
            return redirect("/")

        @app.post("/login", include_in_schema=False)
        async def login(request: Request) -> Response:
            return await _login(request)

        @app.get("/oauth-callback", include_in_schema=False)
        async def oauth_callback(request: Request) -> Response:
            return await _login(request)

        @app.get("/logout", include_in_schema=False)
        async def logout() -> RedirectResponse:
            return redirect("/")

        app.add_middleware(
            SessionMiddleware,
            config=config,
            engine=engine,
            api=api,
            ui=ui,
        )

    @abc.abstractmethod
    def login_page(self, request: Request) -> Response: ...

    @abc.abstractmethod
    def login(self, request: Request) -> Union[schemas.User, Response]: ...


class NoAuth(Auth):
    def login_page(self, request: Request) -> Response:
        # To invoke the login() method below, the client either needs to
        # - POST /login or
        # - GET /oauth-callback
        # Since we cannot instruct a browser to post when sending redirect response, we
        # use the OAuth callback endpoint here, although this has nothing to do with
        # OAuth.
        return redirect("/oauth-callback")

    def login(self, request: Request) -> schemas.User:
        return schemas.User(name=request.headers.get("X-User", default_user()))


class DummyBasicAuth(Auth):
    """Dummy OAuth2 password authentication without requirements.

    !!! danger

        As the name implies, this authentication is just testing or demo purposes and
        should not be used in production.
    """

    def __init__(self) -> None:
        self._password = os.environ.get("RAGNA_DUMMY_BASIC_AUTH_PASSWORD")

    def login_page(
        self,
        request: Request,
        *,
        username: Optional[str] = None,
        fail_reason: Optional[str] = None,
    ) -> HTMLResponse:
        return HTMLResponse(
            templates.render(
                "basic_auth.html", username=username, fail_reason=fail_reason
            )
        )

    async def login(self, request: Request) -> Union[schemas.User, HTMLResponse]:
        async with request.form() as form:
            username = cast(str, form.get("username"))
            password = cast(str, form.get("password"))

        if username is None or password is None:
            # This can only happen if the endpoint is not hit through the login page.
            # Thus, instead of returning the failed login page like below, we just
            # return an error.
            raise RagnaException(
                "Field 'username' or 'password' is missing from the form data.",
                http_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                http_detail=RagnaException.MESSAGE,
            )

        if not username:
            return self.login_page(request, fail_reason="Username cannot be empty")
        elif (self._password is not None and password != self._password) or (
            self._password is None and password != username
        ):
            return self.login_page(
                request, username=username, fail_reason="Password incorrect"
            )

        return schemas.User(name=username)


class GithubOAuth(Auth):
    def __init__(self) -> None:
        # FIXME: requirements
        self._client_id = os.environ["RAGNA_GITHUB_OAUTH_CLIENT_ID"]
        self._client_secret = os.environ["RAGNA_GITHUB_OAUTH_CLIENT_SECRET"]

    def login_page(self, request: Request) -> HTMLResponse:
        return HTMLResponse(
            templates.render(
                "oauth.html",
                service="GitHub",
                url=f"https://github.com/login/oauth/authorize?client_id={self._client_id}",
            )
        )

    async def login(self, request: Request) -> Union[schemas.User, Response]:
        async with httpx.AsyncClient(headers={"Accept": "application/json"}) as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                json={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "code": request.query_params["code"],
                },
            )
            access_token = response.json()["access_token"]
            client.headers["Authorization"] = f"Bearer {access_token}"

            user_data = (await client.get("https://api.github.com/user")).json()

            organizations_data = (
                await client.get(user_data["organizations_url"])
            ).json()
            organizations = {
                organization_data["login"] for organization_data in organizations_data
            }
            if not (organizations & {"Quansight", "Quansight-Labs"}):
                # FIXME: send the login page again with a failure message
                return HTMLResponse("Unauthorized!")

            return schemas.User(name=user_data["login"])
