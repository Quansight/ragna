import abc
import os

import ragna

from ragna.core import (
    Assistant,
    EnvVarRequirement,
    PackageRequirement,
    Requirement,
    Source,
    task_config,
)


class ApiAssistant(Assistant):
    _API_KEY_ENV_VAR: str

    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [
            PackageRequirement("httpx"),
            EnvVarRequirement(cls._API_KEY_ENV_VAR),
        ]

    def __init__(self, config, *, num_retries: int = 2, retry_delay: float = 1.0):
        super().__init__(config)

        import httpx

        self._client = httpx.Client(
            headers={"User-Agent": f"{ragna.__version__}/{self}"},
            timeout=10,
        )
        self._num_retries = num_retries
        self._retry_delay = retry_delay
        self._api_key = os.environ[self._API_KEY_ENV_VAR]

    @task_config(retries=2, retry_delay=1)
    def answer(self, prompt: str, sources: list[Source], *, max_new_tokens: int = 256):
        return self._call_api(prompt, sources, max_new_tokens=max_new_tokens)

    @abc.abstractmethod
    def _call_api(self, prompt: str, sources: list[Source], *, max_new_tokens: int):
        ...
