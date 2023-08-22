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

    class _FailedApiCall(Exception):
        def __init__(self, event, additional_context):
            self.event = event
            self.additional_context = additional_context

    def _failed_api_call(
        self, event="Bad API response", **additional_context
    ) -> NoReturn:
        raise self._FailedApiCall(event, additional_context)

    def complete(self, prompt: str, sources: list[Source], *, chat_config):
        max_new_tokens = chat_config.extra.get("max_new_tokens", 256)

        logger = self.app_config.get_logger(
            name=str(self),
            num_retries=self._num_retries,
            retry_delay=self._retry_delay,
            max_new_tokens=max_new_tokens,
        )

        for try_number in range(self._num_retries + 1):
            try:
                return self._call_api(prompt, sources, max_new_tokens=max_new_tokens)
            except self._FailedApiCall as api_exception:
                logger.warn(
                    api_exception.event,
                    try_number=try_number,
                    **api_exception.additional_context,
                )
            time.sleep(self._retry_delay)

        logger.error("Failed API call")

        return (
            "I'm sorry, but I'm having trouble helping you at this time. "
            "Please retry later. "
            "If this issue persists, please contact your administrator."
        )

    @abc.abstractmethod
    def _call_api(self, prompt: str, sources: list[Source], *, max_new_tokens: int):
        ...
