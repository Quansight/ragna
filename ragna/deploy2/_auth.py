import abc
import os
from typing import Optional, Union

from fastapi import Request, status
from fastapi.responses import Response

from ragna.core import RagnaException

from . import _constants as constants
from ._templates import TemplateResponse
from ._utils import redirect_response
from .schemas import User


class Auth(abc.ABC):
    @abc.abstractmethod
    def login_page(self, request: Request) -> Union[str, Response]:
        ...

    @abc.abstractmethod
    def login(self, request: Request) -> Union[User, str, Response]:
        ...


class NoAuth(Auth):
    def login_page(self, request: Request) -> Response:
        return redirect_response(
            constants.UI_PREFIX, htmx=request, status_code=status.HTTP_303_SEE_OTHER
        )

    def login(self, request: Request) -> User:
        return User(username=request.headers.get("X-User", "User"))


class DummyBasicAuth(Auth):
    """Demo OAuth2 password authentication without requirements.

    !!! danger

        As the name implies, this authentication is just for demo purposes and should
        not be used in production.
    """

    def __init__(self) -> None:
        self._password = os.environ.get("RAGNA_DUMMY_BASIC_AUTH_PASSWORD")

    def login_page(
        self, request: Request, *, fail_reason: Optional[str] = None
    ) -> Union[str, Response]:
        return TemplateResponse(
            name="login.html",
            context={"request": request},
        )

    async def login(self, request: Request) -> Union[User, str, Response]:
        async with request.form() as form:
            username = form.get("username")
            password = form.get("password")

        if username is None or password is None:
            # This can only happen if the endpoint is not hit through the endpoint.
            # Thus, instead of returning the failed login page like below, we just
            # return an error.
            raise RagnaException(
                "Field 'username' or 'password' is missing from the form data.",
                http_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                http_detail=RagnaException.MESSAGE,
            )

        if (self._password is not None and password != self._password) or (
            self._password is None and password != username
        ):
            return self.login_page(request, fail_reason="Unauthorized")

        return User(username=username)
