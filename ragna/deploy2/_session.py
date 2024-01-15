import abc
import json
import os
import secrets
import time
import uuid
from typing import Awaitable, Callable, Optional, cast

import jwt
import pydantic
from fastapi import Request
from fastapi.responses import JSONResponse, Response
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

        # either unknown route or something on the root router. Let it pass since this doesn't need a session
        return await call_next(request)

    _JWT_SECRET = os.environ.get("RAGNA_TOKEN_SECRET", secrets.token_urlsafe(32)[:32])
    _JWT_ALGORITHM = "HS256"

    async def _api_dispatch(self, request: Request, call_next: CallNext) -> Response:
        session_id = self._extract_session_id_from_token(request)

        if session_id is None:
            is_auth = request.url.path == constants.API_TOKEN_ENDPOINT
            if not is_auth:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            session_id = str(uuid.uuid4())
        else:
            is_auth = False

        request.state.session = self._sessions[session_id] if not is_auth else None
        response = await call_next(request)
        self._sessions[session_id] = request.state.session

        if is_auth:
            # The token endpoint only returns a dummy response that we overwrite here.
            # We do this to have token generation and validation in one place.
            return JSONResponse(json.dumps(self._forge_token(session_id)))
        else:
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

        if session_id is None:
            is_auth = request.url.path == constants.UI_LOGIN_ENDPOINT
            if not is_auth:
                return redirect_response(
                    constants.UI_LOGIN_ENDPOINT, htmx=request, status_code=303
                )

            session_id = str(uuid.uuid4())
        else:
            # this is here because it is not user defined anyway and like this we can
            # avoid the roundtrip to and actual endpoint
            if request.url.path == constants.UI_LOGOUT_ENDPOINT:
                del self._sessions[session_id]
                response = redirect_response(
                    constants.UI_LOGIN_ENDPOINT, htmx=request, status_code=303
                )
                response.delete_cookie(
                    key=self._COOKIE_NAME, httponly=True, samesite="strict"
                )
                return response

            is_auth = False

        request.state.session = self._sessions[session_id] if not is_auth else None
        response = await call_next(request)

        # FIXME: what happens when the login attempt fails

        self._sessions[session_id] = request.state.session

        if is_auth:
            response.set_cookie(
                key=self._COOKIE_NAME,
                value=session_id,
                expires=self._config.deploy.cookie_expires,
                httponly=True,
                samesite="strict",
            )

        return response
