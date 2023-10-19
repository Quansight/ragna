import abc
import os
import secrets
import time

import jwt
from fastapi import HTTPException, Request, status
from fastapi.security.utils import get_authorization_scheme_param

from ._utils import default_user


class Authentication(abc.ABC):
    @abc.abstractmethod
    async def create_token(self, request: Request) -> str:
        pass

    @abc.abstractmethod
    async def get_user(self, request: Request) -> str:
        pass


class NoAuthentication(Authentication):
    def __init__(self):
        self._default_user = default_user()

    async def create_token(self, request: Request) -> str:
        return request.headers.get("X-User", self._default_user)

    async def get_user(self, request: Request) -> str:
        authorization = request.headers.get("Authorization")
        scheme, token = get_authorization_scheme_param(authorization)
        if authorization and scheme.lower() == "bearer":
            return token

        return await self.get_user(request)


class RagnaDemoAuthentication(Authentication):
    def __init__(self):
        self._password = os.environ.get("AI_PROXY_DEMO_AUTHENTICATION_PASSWORD")

    _JWT_SECRET = secrets.token_urlsafe(32)
    _JWT_ALGORITHM = "HS256"

    _ONE_WEEK = 60 * 60 * 24 * 7

    async def create_token(self, request: Request) -> str:
        async with request.form() as form:
            username = form.get("username")
            password = form.get("password")

        if username is None or password is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY)

        if self._password is not None and password != self._password:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        return jwt.encode(
            payload={"user": username, "exp": time.time() + self._ONE_WEEK},
            key=self._JWT_SECRET,
            algorithm=self._JWT_ALGORITHM,
        )

    async def get_user(self, request: Request) -> str:
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
                token, key=self._JWT_SECRET, algorithms=self._JWT_ALGORITHM
            )
        except (jwt.InvalidSignatureError, jwt.ExpiredSignatureError):
            raise unauthorized

        return payload["user"]
