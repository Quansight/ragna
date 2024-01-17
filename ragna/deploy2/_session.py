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

from . import _constants as constants
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
        self._dct: dict[str, Session] = {}

    def __setitem__(self, session_id: str, session: Session):
        self._dct[session_id] = session

    def __getitem__(self, session_id: str) -> Session:
        return self._dct[session_id]

    def __delitem__(self, session_id: str) -> None:
        del self._dct[session_id]


# TODO: add a redis variant for proper deployments


CallNext = Callable[[Request], Awaitable[Response]]


class SessionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, config, deploy_api: bool, deploy_ui: bool):
        super().__init__(app)
        self._sessions = InMemorySessionStorage(config.deploy.session_storage_url)
        self._config = config
        self._deploy_api = deploy_api
        self._deploy_ui = deploy_ui

    async def dispatch(self, request: Request, call_next: CallNext) -> Response:
        path = request.url.path
        if self._deploy_api and path.startswith(constants.API_PREFIX):
            return await self._api_dispatch(request, call_next)
        elif self._deploy_ui and path.startswith(constants.UI_PREFIX):
            return await self._ui_dispatch(request, call_next)
        else:
            # Either an unknown route or something on the root router. In any case, this
            # doesn't need a session so we can let it pass.
            return await call_next(request)

    _JWT_SECRET = os.environ.get("RAGNA_TOKEN_SECRET", secrets.token_urlsafe(32)[:32])
    _JWT_ALGORITHM = "HS256"

    async def _api_dispatch(self, request: Request, call_next: CallNext) -> Response:
        session_id = self._extract_session_id_from_token(request)
        session = self._sessions.get(session_id) if session_id is not None else None

        if session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )

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

    def _forge_token(self, session_id: str) -> str:
        return jwt.encode(
            payload={
                "session-id": session_id,
                "exp": time.time() + self._config.deploy.token_expires,
            },
            key=self._JWT_SECRET,
            algorithm=self._JWT_ALGORITHM,
        )

    _COOKIE_NAME = "Ragna"

    async def _ui_dispatch(self, request: Request, call_next: CallNext) -> Response:
        session_id = request.cookies.get(self._COOKIE_NAME)
        cookie_available = session_id is not None
        session = self._sessions.get(session_id) if cookie_available else None
        session_available = session is not None

        if not cookie_available:
            if request.url.path != constants.UI_LOGIN_ENDPOINT:
                return redirect_response(
                    constants.UI_LOGIN_ENDPOINT, htmx=request, status_code=303
                )

            session_id = str(uuid.uuid4())
        elif not session_available:
            response = redirect_response(
                constants.UI_LOGIN_ENDPOINT, htmx=request, status_code=303
            )
            self._delete_cookie(response)
            return response

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
            expires=self._config.deploy.cookie_expires,
            httponly=True,
            samesite="strict",
        )

    def _delete_cookie(self, response: Response):
        response.delete_cookie(key=self._COOKIE_NAME, httponly=True, samesite="strict")


async def get_session(request: Request) -> Session:
    return request.state.session


SessionDependency = Annotated[Session, Depends(get_session)]
