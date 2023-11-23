import abc
import os
import secrets
import time
from typing import cast

import jwt
import rich
from fastapi import HTTPException, Request, status
from fastapi.security.utils import get_authorization_scheme_param


class Authentication(abc.ABC):
    """Abstract base class for authentication used by the REST API."""

    @abc.abstractmethod
    async def create_token(self, request: Request) -> str:
        """Authenticate user and create an authorization token.

        Args:
            request: Request send to the `/token` endpoint of the REST API.

        Returns:
            Authorization token.
        """
        pass

    @abc.abstractmethod
    async def get_user(self, request: Request) -> str:
        """
        Args:
            request: Request send to any endpoint of the REST API that requires
                authorization.

        Returns:
            Authorized user.
        """
        pass


class RagnaDemoAuthentication(Authentication):
    """Demo OAuth2 password authentication without requirements.

    !!! danger

        As the name implies, this authentication is just for demo purposes and should
        not be used in production.
    """

    def __init__(self) -> None:
        msg = f"INFO:\t{type(self).__name__}: You can log in with any username"
        self._password = os.environ.get("RAGNA_DEMO_AUTHENTICATION_PASSWORD")
        if self._password is None:
            msg = f"{msg} and a matching password."
        else:
            msg = f"{msg} and the password {self._password}"
        rich.print(msg)

    _JWT_SECRET = os.environ.get(
        "RAGNA_DEMO_AUTHENTICATION_SECRET", secrets.token_urlsafe(32)[:32]
    )
    _JWT_ALGORITHM = "HS256"
    _JWT_TTL = int(os.environ.get("RAGNA_DEMO_AUTHENTICATION_TTL", 60 * 60 * 24 * 7))

    async def create_token(self, request: Request) -> str:
        """Authenticate user and create an authorization token.

        User name is arbitrary. Authentication is possible in two ways:

        1. If the `RAGNA_DEMO_AUTHENTICATION_PASSWORD` environment variable is set, the
           password is checked against that.
        2. Otherwise, the password has to match the user name.

        Args:
            request: Request send to the `/token` endpoint of the REST API. Must include
                the `"username"` and `"password"` as form data.

        Returns:
            Authorization [JWT](https://jwt.io/) that expires after one week.
        """
        async with request.form() as form:
            username = form.get("username")
            password = form.get("password")

        if username is None or password is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY)

        if (self._password is not None and password != self._password) or (
            self._password is None and password != username
        ):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        return jwt.encode(
            payload={"user": username, "exp": time.time() + self._JWT_TTL},
            key=self._JWT_SECRET,
            algorithm=self._JWT_ALGORITHM,
        )

    async def get_user(self, request: Request) -> str:
        """Get user from an authorization token.

        Token has to be supplied in the
        [Bearer authentication scheme](https://swagger.io/docs/specification/authentication/bearer-authentication/),
        i.e. including a `Authorization: Bearer {token}` header.

        Args:
            request: Request send to any endpoint of the REST API that requires
                authorization.

        Returns:
            Authorized user.
        """

        unauthorized = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

        authorization = request.headers.get("Authorization")
        scheme, token = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            raise unauthorized

        try:
            payload = jwt.decode(
                token, key=self._JWT_SECRET, algorithms=[self._JWT_ALGORITHM]
            )
        except (jwt.InvalidSignatureError, jwt.ExpiredSignatureError):
            raise unauthorized

        return cast(str, payload["user"])
