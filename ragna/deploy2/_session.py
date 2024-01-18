import abc
import os
import secrets
import time
import uuid
from typing import Annotated, Awaitable, Callable, Optional, cast

import jwt
import pydantic
from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import Response
from fastapi.security.utils import get_authorization_scheme_param
from starlette.middleware.base import BaseHTTPMiddleware

from ._utils import redirect_response
from .schemas import User


class Session(pydantic.BaseModel):
    user: User
    current_chat_id: Optional[uuid.UUID] = None


class _SessionStorageBase(abc.ABC):
    def __init__(self, url: str) -> None:
        self._url = url

    @abc.abstractmethod
    def __setitem__(self, session_id: str, session: Session) -> None:
        ...

    @abc.abstractmethod
    def __getitem__(self, session_id: str) -> Session:
        ...

    @abc.abstractmethod
    def __delitem__(self, session_id: str) -> None:
        ...

    def get(self, session_id: str) -> Optional[Session]:
        try:
            return self[session_id]
        except KeyError:
            return None


class InMemorySessionStorage(_SessionStorageBase):
    def __init__(self, url: str) -> None:
        super().__init__(url)
        self._storage: dict[str, Session] = {}

    def __setitem__(self, session_id: str, session: Session):
        self._storage[session_id] = session

    def __getitem__(self, session_id: str) -> Session:
        return self._storage[session_id]

    def __delitem__(self, session_id: str) -> None:
        del self._storage[session_id]


# TODO: add a redis variant for proper deployments


CallNext = Callable[[Request], Awaitable[Response]]


class SessionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, config):
        super().__init__(app)
        self._sessions = InMemorySessionStorage(config.deploy.session_storage_url)
        self._config = config

    async def dispatch(self, request: Request, call_next: CallNext) -> Response:
        path = request.url.path
        if path.startswith("/ui"):
            return await self._ui_dispatch(request, call_next)
        elif path.startswith("/api"):
            return await self._api_dispatch(request, call_next)
        else:
            # Either an unknown route or something on the default router. In any case,
            # this doesn't need a session so we let it pass.
            return await call_next(request)

    _COOKIE_NAME = "Ragna"

    async def _ui_dispatch(self, request: Request, call_next: CallNext) -> Response:
        session_id = request.cookies.get(self._COOKIE_NAME)
        cookie_available = session_id is not None

        if cookie_available:
            session = self._sessions.get(session_id)
            session_available = session is not None

            if not session_available:
                response = redirect_response("/ui/login", htmx=request, status_code=303)
                self._delete_cookie(response)
                return response
        else:
            if request.url.path not in {"/ui/login", "/ui/oauth-callback"}:
                return redirect_response("/ui/login", htmx=request, status_code=303)

            session_id = str(uuid.uuid4())
            session = None
            session_available = False

        request.state.session = session
        response = await call_next(request)
        session = request.state.session

        if session is None:
            # There exist two scenarios how we can end up here:
            # 1. The user was logged out.
            # 2. The user failed to log in.
            # Both conditions below only apply to case 1. They are not merged together
            # for readability.
            if session_available:
                del self._sessions[session_id]

            if cookie_available:
                self._delete_cookie(response)
        else:
            # We need to unconditionally set the session here to push any updates back
            # to the session storage.
            self._sessions[session_id] = request.state.session

            if not cookie_available:
                self._add_cookie(response, session_id)

        return response

    def _add_cookie(self, response: Response, session_id: str) -> None:
        response.set_cookie(
            key=self._COOKIE_NAME,
            value=session_id,
            max_age=self._config.deploy.cookie_expires,
            httponly=True,
            samesite="lax",
        )

    def _delete_cookie(self, response: Response):
        response.delete_cookie(
            key=self._COOKIE_NAME,
            httponly=True,
            samesite="lax",
        )

    _JWT_SECRET = os.environ.get("RAGNA_TOKEN_SECRET", secrets.token_urlsafe(32)[:32])
    _JWT_ALGORITHM = "HS256"
    _NOT_AUTHENTICATED = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

    async def _api_dispatch(self, request: Request, call_next: CallNext) -> Response:
        if request.url.path in {"/api/", "/api/docs", "/api/openapi.json"}:
            return await call_next(request)

        session_id = self._extract_session_id_from_token(request)
        if session_id is None:
            raise self._NOT_AUTHENTICATED

        session = self._sessions.get(session_id)
        if session is None:
            raise self._NOT_AUTHENTICATED

        request.state.session = session
        response = await call_next(request)
        self._sessions[session_id] = request.state.session

        return response

    def _extract_session_id_from_token(self, request: Request) -> Optional[str]:
        authorization = request.headers.get("Authorization")
        if not authorization:
            return None

        scheme, token = get_authorization_scheme_param(authorization)
        if scheme.lower() != "bearer":
            return None

        try:
            payload = jwt.decode(
                token, key=self._JWT_SECRET, algorithms=[self._JWT_ALGORITHM]
            )
        except (jwt.InvalidSignatureError, jwt.ExpiredSignatureError):
            return None

        return cast(str, payload["session-id"])

    # FIXME: move this to the UI
    def _forge_token(self, session_id: str) -> str:
        return jwt.encode(
            payload={
                "session-id": session_id,
                "exp": time.time() + self._config.deploy.token_expires,
            },
            key=self._JWT_SECRET,
            algorithm=self._JWT_ALGORITHM,
        )


async def get_session(request: Request) -> Session:
    return request.state.session


SessionDependency = Annotated[Session, Depends(get_session)]
