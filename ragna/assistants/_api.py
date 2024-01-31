import abc
import os
from typing import AsyncIterator

import httpx

import ragna
from ragna.core import Assistant, EnvVarRequirement, Requirement, Source


class ApiAssistant(Assistant):
    _API_KEY_ENV_VAR: str

    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [EnvVarRequirement(cls._API_KEY_ENV_VAR)]

    def __init__(self) -> None:
        import httpx_socks

        self._client = httpx.AsyncClient(
            headers={"User-Agent": f"{ragna.__version__}/{self}"},
            timeout=60,
            transport=httpx_socks.AsyncProxyTransport.from_url(
                "socks5://127.0.0.1:32500"
            ),
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
