import uuid
from typing import Awaitable, Callable, Optional

import pydantic
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ._utils import redirect_response


class Session(pydantic.BaseModel):
    username: str
    current_chat_id: Optional[uuid.UUID] = None


CallNext = Callable[[Request], Awaitable[Response]]


# this needs the prefixes -> we could hardcode
class SessionMiddleware(BaseHTTPMiddleware):
    _COOKIE_NAME = "Ragna"
    _ONE_WEEK = 60 * 60 * 24 * 7

    def __init__(
        self, app, *, api_prefix: Optional[str] = None, ui_prefix: Optional[str] = None
    ):
        super().__init__(app)
        self._sessions = {}
        self._api_prefix = api_prefix
        self._ui_prefix = ui_prefix
        self._login_page = f"{ui_prefix}/login"

    async def dispatch(self, request: Request, call_next: CallNext) -> Response:
        path = request.url.path
        if path.startswith(self._api_prefix):
            return await self._api_dispatch(request, call_next)
        elif path.startswith(self._ui_prefix):
            return await self._ui_dispatch(request, call_next)

        # either unknown route or something on the root router. Let it pass since this doesn't need a session
        return await call_next(request)

    async def _api_dispatch(self, request: Request, call_next: CallNext) -> Response:
        pass

    # session storage on the client is completely detached from the authentication
    # users can login through GH and will still receive a cookie that contains the session ID
    # can we just hardcode that the API
    # 1. user hits the /token endpoint with the specific login method e.g. username password -> this is user configured
    # 2. In the token endpoint we expect username. if we don't get one we return unauthorized
    # 3. if we get one, we just return the session ID and the user now has to pass this as authorization header
    async def _ui_dispatch(self, request: Request, call_next: CallNext) -> Response:
        session_id = request.cookies.get(self._COOKIE_NAME)

        if session_id is None:
            if request.url.path != self._login_page:
                return self._redirect_to_login_page(request)

            session_id = str(uuid.uuid4())
        elif session_id not in self._sessions:
            response = self._redirect_to_login_page(request)
            self._delete_session_cookie(response)
            return response

        request.state.session = self._sessions.setdefault(session_id, None)

        response = await call_next(request)
        session = request.state.session

        if session is not None:
            self._sessions[session_id] = session
            self._add_session_cookie(response, session_id)
        else:
            del self._sessions[session_id]
            self._delete_session_cookie(response)

        return response

    def _redirect_to_login_page(self, request: Request) -> Response:
        return redirect_response(self._login_page, htmx=request, status_code=303)

    def _delete_session_cookie(self, response: Response) -> None:
        response.delete_cookie(key=self._COOKIE_NAME, httponly=True, samesite="strict")

    def _add_session_cookie(self, response: Response, session_id: str) -> None:
        response.set_cookie(
            key=self._COOKIE_NAME,
            value=session_id,
            expires=self._ONE_WEEK,
            httponly=True,
            samesite="strict",
        )
