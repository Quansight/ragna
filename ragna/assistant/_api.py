import abc
import os

from ragna.core import (
    Assistant,
    EnvVarRequirement,
    PackageRequirement,
    RagnaException,
    Requirement,
    Source,
)


# This needs to be somewhere else
def job_config(**kwargs):
    def decorator(fn):
        fn.__ragna_job_kwargs__ = kwargs
        return fn

    return decorator


class ApiException(RagnaException):
    def __init__(self, event="Failed API call", **additional_context):
        self.event = event
        self.additional_context = additional_context


class AssistantApi(Assistant):
    _API_KEY_ENV_VAR: str

    def __init__(self, config, *, num_retries: int = 2, retry_delay: float = 1.0):
        super().__init__(config)
        self._num_retries = num_retries
        self._retry_delay = retry_delay
        self._api_key = os.environ[self._API_KEY_ENV_VAR]

    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [
            PackageRequirement("requests"),
            EnvVarRequirement(cls._API_KEY_ENV_VAR),
        ]

    # FIXME: add retries
    @job_config()
    def answer(self, prompt: str, sources: list[Source], *, max_new_tokens: int = 256):
        try:
            return self._call_api(prompt, sources, max_new_tokens=max_new_tokens)
        except ApiException as api_exception:
            self.logger.error(
                api_exception.event,
                **api_exception.additional_context,
                llm_name=str(self),
            )
        except Exception:
            # FIXME: properly log exception here
            self.logger.error("ADDME", llm_name=str(self))

        return (
            "I'm sorry, but I'm having trouble helping you at this time. "
            "Please retry later. "
            "If this issue persists, please contact your administrator."
        )

    @abc.abstractmethod
    def _call_api(self, prompt: str, sources: list[Source], *, max_new_tokens: int):
        ...
