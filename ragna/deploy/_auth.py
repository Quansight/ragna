import abc
import os
from typing import Optional, Union

import httpx
from fastapi import Request, status
from fastapi.responses import HTMLResponse, Response

from ragna._utils import default_user
from ragna.core import RagnaException

from . import _templates as templates
from ._utils import redirect
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
        # To invoke the login() method below, the client either needs to
        # - POST /login or
        # - GET /oauth-callback
        # Since we cannot instruct a browser to post when sending redirect response, we
        # use the OAuth callback endpoint here, although this has nothing to do with
        # OAuth.
        return redirect("/oauth-callback")

    def login(self, request: Request) -> User:
        return User(username=request.headers.get("X-User", default_user()))


class DummyBasicAuth(Auth):
    """Dummy OAuth2 password authentication without requirements.

    !!! danger

        As the name implies, this authentication is just testing or demo purposes and
        should not be used in production.
    """

    def __init__(self) -> None:
        self._password = os.environ.get("RAGNA_DUMMY_BASIC_AUTH_PASSWORD")

    def login_page(
        self, request: Request, *, fail_reason: Optional[str] = None
    ) -> HTMLResponse:
        return HTMLResponse(templates.render("basic_auth.html"))

    async def login(self, request: Request) -> Union[User, HTMLResponse]:
        async with request.form() as form:
            username = form.get("username")
            password = form.get("password")

        if username is None or password is None:
            # This can only happen if the endpoint is not hit through the login page.
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
            # FIXME: send the login page again with a failure message
            return HTMLResponse("Unauthorized!")

        return User(username=username)


class GithubOAuth(Auth):
    def __init__(self):
        # FIXME: requirements
        self._client_id = os.environ["RAGNA_GITHUB_OAUTH_CLIENT_ID"]
        self._client_secret = os.environ["RAGNA_GITHUB_OAUTH_CLIENT_SECRET"]

    def login_page(self, request) -> HTMLResponse:
        return HTMLResponse(
            templates.render(
                "oauth.html",
                service="GitHub",
                url=f"https://github.com/login/oauth/authorize?client_id={self._client_id}",
            )
        )

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

            organizations_data = (
                await client.get(user_data["organizations_url"])
            ).json()
            organizations = {
                organization_data["login"] for organization_data in organizations_data
            }
            if not (organizations & {"Quansight", "Quansight-Labs"}):
                # FIXME: send the login page again with a failure message
                return HTMLResponse("Unauthorized!")

            return User(username=user_data["login"])
