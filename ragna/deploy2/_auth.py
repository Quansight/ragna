import os
from typing import Any, Union

from fastapi import Request
from fastapi.responses import Response

from ragna.core import RagnaException


class Auth:
    def login(self, request: Request) -> Any:
        pass

    def login_page(self) -> Union[str, Response]:
        pass

    def failed_login_page(self, context: Any) -> Union[str, Response]:
        pass


# def add_auth(app, *, auth: Auth, prefix: str):
#     @app.get(f"{prefix}/login")
#     async def login() -> Response:
#         return auth.login_page()
#
#     @app.post(f"{prefix}/login")
#     async def login(request: Request):
#         user_data = auth.login(request)
#         # put it into the session
#         return redirect_response(prefix, status_code=303)
#
#     @app.post(f"{prefix}/logout")
#     async def logout(request: Request):
#         request.state.session = None
#         return redirect_response(f"{prefix}/login", htmx=request, status_code=303)


class NoAuth(Auth):
    pass


class DummyBasicAuth(Auth):
    """Demo OAuth2 password authentication without requirements.

    !!! danger

        As the name implies, this authentication is just for demo purposes and should
        not be used in production.
    """

    async def login(self, request: Request) -> Optional[str]:
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

    def __init__(self) -> None:
        self._password = os.environ.get("RAGNA_DUMMY_BASIC_AUTH_PASSWORD")

    def login_page(self) -> Union[str, Response]:
        pass
