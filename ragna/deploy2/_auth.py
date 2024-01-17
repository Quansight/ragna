import abc
import os
from typing import Optional, Union

import httpx
from fastapi import Request, status
from fastapi.responses import Response

from ragna.core import RagnaException

from ._templates import TemplateResponse
from ._utils import redirect_response
from .schemas import User


class Auth(abc.ABC):
    @abc.abstractmethod
    def login_page(self, request: Request) -> Response:
        ...

    @abc.abstractmethod
    def login(self, request: Request) -> Union[User, Response]:
        ...


class NoAuth(Auth):
    def login_page(self, request: Request) -> Response:
        return redirect_response(
            "/ui", htmx=request, status_code=status.HTTP_303_SEE_OTHER
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


class GithubOauth(Auth):
    def __init__(self):
        self._client_id = os.environ["RAGNA_GITHUB_OAUTH_CLIENT_ID"]
        self._client_secret = os.environ["RAGNA_GITHUB_OAUTH_CLIENT_SECRET"]

    def login_page(self, request) -> Response:
        pass

    async def login(self, request):
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
            return User(username=user_data["login"])
