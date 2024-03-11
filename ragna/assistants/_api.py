import abc
import contextlib
import json
import os
from typing import AsyncIterator

import httpx
from httpx import Response

import ragna
from ragna.core import Assistant, EnvVarRequirement, RagnaException, Requirement, Source


class ApiAssistant(Assistant):
    _API_KEY_ENV_VAR: str

    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [EnvVarRequirement(cls._API_KEY_ENV_VAR)]

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            headers={"User-Agent": f"{ragna.__version__}/{self}"},
            timeout=60,
        )
        self._api_key = os.environ[self._API_KEY_ENV_VAR]

    async def answer(
        self, prompt: str, sources: list[Source], *, max_new_tokens: int = 256
    ) -> AsyncIterator[str]:
        async for chunk in self._call_api(  # type: ignore[attr-defined, misc]
            prompt, sources, max_new_tokens=max_new_tokens
        ):
            yield chunk

    @abc.abstractmethod
    async def _call_api(
        self, prompt: str, sources: list[Source], *, max_new_tokens: int
    ) -> AsyncIterator[str]:
        ...

    async def _assert_api_call_is_success(self, response: Response) -> None:
        if response.is_success:
            return

        content = await response.aread()
        with contextlib.suppress(Exception):
            content = json.loads(content)

        raise RagnaException(
            "API call failed",
            request_method=response.request.method,
            request_url=str(response.request.url),
            response_status_code=response.status_code,
            response_content=content,
        )
