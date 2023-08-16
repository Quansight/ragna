import abc
import os

from ora.extensions import (
    EnvironmentVariableRequirement,
    Llm,
    PackageRequirement,
    Requirement,
)


class LlmApi(Llm):
    _API_KEY_ENV_VAR: str

    def __init__(self, app_config):
        super().__init__(app_config)
        self._api_key = os.environ[self._API_KEY_ENV_VAR]

    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [
            PackageRequirement("requests"),
            EnvironmentVariableRequirement(cls._API_KEY_ENV_VAR),
        ]

    def complete(self, prompt: str, chat_config):
        # TODO: add retries
        return self._call_api(prompt, chat_config)

    @abc.abstractmethod
    def _call_api(self, prompt: str, chat_config):
        ...
