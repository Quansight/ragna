import abc
import os

import ragna
from ragna.core import (
    Assistant,
    Config,
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

    def __init__(self, config: Config) -> None:
        super().__init__(config)

        import httpx

        self._client = httpx.Client(
            headers={"User-Agent": f"{ragna.__version__}/{self}"},
            timeout=30,
        )
        self._api_key = os.environ[self._API_KEY_ENV_VAR]

    @task_config(retries=2, retry_delay=1)
    def answer(
        self, prompt: str, sources: list[Source], *, max_new_tokens: int = 256
    ) -> str:
        return self._call_api(prompt, sources, max_new_tokens=max_new_tokens)

    @abc.abstractmethod
    def _call_api(
        self, prompt: str, sources: list[Source], *, max_new_tokens: int
    ) -> str:
        ...
