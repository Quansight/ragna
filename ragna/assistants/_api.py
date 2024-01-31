import abc
import os
from typing import Any, AsyncIterator, Iterator

import httpx

import ragna
from ragna._utils import as_async_iterator
from ragna.core import Assistant, EnvVarRequirement, Requirement, Source


class ApiAssistant(Assistant):
    _API_KEY_ENV_VAR: str

    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [EnvVarRequirement(cls._API_KEY_ENV_VAR)]

    def __init__(self) -> None:
        self._api_key = os.environ[self._API_KEY_ENV_VAR]

        kwargs: dict[str, Any] = dict(
            headers={"User-Agent": f"{ragna.__version__}/{self}"},
            timeout=60,
        )
        self._sync_client = httpx.Client(**kwargs)
        self._async_client = httpx.AsyncClient(**kwargs)

    async def answer(
        self, prompt: str, sources: list[Source], *, max_new_tokens: int = 256
    ) -> AsyncIterator[str]:
        async for chunk in as_async_iterator(
            self._call_api,
            prompt,
            sources,
            max_new_tokens=max_new_tokens,
        ):
            yield chunk

    @abc.abstractmethod
    def _call_api(
        self, prompt: str, sources: list[Source], *, max_new_tokens: int
    ) -> Iterator[str]:
        ...
