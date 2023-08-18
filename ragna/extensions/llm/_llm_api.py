import abc
import os

from ragna.extensions import (
    EnvironmentVariableRequirement,
    Llm,
    PackageRequirement,
    Requirement,
    Source,
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

    def complete(self, prompt: str, sources: list[Source], *, chat_config):
        # TODO: add retries
        return self._call_api(prompt, sources, chat_config=chat_config)

    @abc.abstractmethod
    def _call_api(self, prompt: str, sources: list[Source], *, chat_config):
        ...
