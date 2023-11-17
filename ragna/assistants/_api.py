import abc
import os

import ragna
from ragna.core import (
    Assistant,
    EnvVarRequirement,
    Requirement,
    Source,
    task_config,
)


class ApiAssistant(Assistant):
    _API_KEY_ENV_VAR: str

    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [EnvVarRequirement(cls._API_KEY_ENV_VAR)]

    def __init__(self) -> None:
        import httpx

        self._client = httpx.AsyncClient(
            headers={"User-Agent": f"{ragna.__version__}/{self}"},
            timeout=60,
        )
        self._api_key = os.environ[self._API_KEY_ENV_VAR]

    @task_config(retries=2, retry_delay=1)
    async def answer(
        self, prompt: str, sources: list[Source], *, max_new_tokens: int = 256
    ) -> str:
        return await self._call_api(prompt, sources, max_new_tokens=max_new_tokens)

    @abc.abstractmethod
    async def _call_api(
        self, prompt: str, sources: list[Source], *, max_new_tokens: int
    ) -> str:
        ...
