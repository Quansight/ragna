import abc
import os
import time

from typing import NoReturn

from ragna.extensions import (
    EnvironmentVariableRequirement,
    Llm,
    PackageRequirement,
    Requirement,
    Source,
)


class LlmApi(Llm):
    _API_KEY_ENV_VAR: str

    def __init__(self, app_config, num_retries: int = 2, retry_delay: float = 1.0):
        super().__init__(app_config)
        self._num_retries = num_retries
        self._retry_delay = retry_delay
        self._api_key = os.environ[self._API_KEY_ENV_VAR]

    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [
            PackageRequirement("requests"),
            EnvironmentVariableRequirement(cls._API_KEY_ENV_VAR),
        ]

    class _ApiException(Exception):
        pass

    def _failed_api_call(self, reason: str) -> NoReturn:
        raise self._ApiException(reason)

    def complete(self, prompt: str, sources: list[Source], *, chat_config):
        max_new_tokens = chat_config.extra.get("max_new_tokens", 256)

        for n in range(self._num_retries + 1):
            try:
                return self._call_api(prompt, sources, max_new_tokens=max_new_tokens)
            except self._ApiException as error:
                # TODO: log this
                print(f"{n + 1}. call to external API failed: {error}")
            time.sleep(self._retry_delay)

        raise RuntimeError

    @abc.abstractmethod
    def _call_api(self, prompt: str, sources: list[Source], *, max_new_tokens: int):
        ...
