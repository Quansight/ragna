import abc
import os

import httpx

import ragna

from ragna.core import (
    Assistant,
    EnvVarRequirement,
    PackageRequirement,
    RagnaException,
    Requirement,
    Source,
)


class ApiException(RagnaException):
    def __init__(self, event="Failed API call", **additional_context):
        self.event = event
        self.additional_context = additional_context


class AssistantApi(Assistant):
    _API_KEY_ENV_VAR: str

    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [
            PackageRequirement("httpx"),
            EnvVarRequirement(cls._API_KEY_ENV_VAR),
        ]

    def __init__(self, config, *, num_retries: int = 2, retry_delay: float = 1.0):
        super().__init__(config)
        self._client = httpx.Client(
            headers={"User-Agent": f"{ragna.__version__}/{self}"}
        )
        self._num_retries = num_retries
        self._retry_delay = retry_delay
        self._api_key = os.environ[self._API_KEY_ENV_VAR]

    # FIXME: add retries with ragna.core.task_config. Note that for this to work, we
    #  need to actually raise here
    def answer(self, prompt: str, sources: list[Source], *, max_new_tokens: int = 256):
        try:
            return self._call_api(prompt, sources, max_new_tokens=max_new_tokens)
        except ApiException as api_exception:
            self.logger.error(
                api_exception.event,
                **api_exception.additional_context,
                llm_name=str(self),
            )

        return (
            "I'm sorry, but I'm having trouble helping you at this time. "
            "Please retry later. "
            "If this issue persists, please contact your administrator."
        )

    @abc.abstractmethod
    def _call_api(self, prompt: str, sources: list[Source], *, max_new_tokens: int):
        ...
