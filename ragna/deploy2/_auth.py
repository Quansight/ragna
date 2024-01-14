import os
from typing import Union

from fastapi import Request
from fastapi.responses import Response

from ragna.core import RagnaException

from ._utils import redirect_response


class Auth:
    def login_page(self) -> Union[str, Response]:
        pass

    def login(self, request: Request):
        pass

    def token(self, request: Request):
        pass


def add_auth(app, *, auth: Auth, prefix: str):
    @app.get(f"{prefix}/login")
    async def login() -> Response:
        return auth.login_page()

    @app.post(f"{prefix}/login")
    async def login(request: Request):
        user_data = auth.login(request)
        # put it into the session
        return redirect_response(prefix, status_code=303)

    @app.post(f"{prefix}/logout")
    async def logout(request: Request):
        request.state.session = None
        return redirect_response(f"{prefix}/login", htmx=request, status_code=303)


class NoAuth(Auth):
    pass


class DummyBasicAuth(Auth):
    """Demo OAuth2 password authentication without requirements.

    !!! danger

        As the name implies, this authentication is just for demo purposes and should
        not be used in production.
    """

    def __init__(self) -> None:
        self._password = os.environ.get("RAGNA_DUMMY_BASIC_AUTH_PASSWORD")

    def login_page(self) -> Union[str, Response]:
        pass

    async def login(self, request: Request) -> str:
        async with request.form() as form:
            username = form.get("username")
            password = form.get("password")

        if username is None:
            raise RagnaException(
                "Field 'username' is missing as part of the form data.",
                http_status_code=422,
                http_detail=RagnaException.MESSAGE,
            )
        elif password is None:
            raise RagnaException(
                "Field 'password' is missing as part of the form data.",
                http_status_code=422,
                http_detail=RagnaException.MESSAGE,
            )

        if (self._password is not None and password != self._password) or (
            self._password is None and password != username
        ):
            raise RagnaException("Unauthorized", http_status_code=401)

        return username

    async def token(self, request: Request) -> str:
        pass

    _JWT_SECRET = os.environ.get(
        "RAGNA_DEMO_AUTHENTICATION_SECRET", secrets.token_urlsafe(32)[:32]
    )
    _JWT_ALGORITHM = "HS256"
    _JWT_TTL = int(os.environ.get("RAGNA_DEMO_AUTHENTICATION_TTL", 60 * 60 * 24 * 7))
