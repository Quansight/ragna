from ora.extensions import hookimpl

from ._llm_api import LlmApi


class OpenaiLlmApi(LlmApi):
    _API_KEY_ENV_VAR = "OPENAI_API_KEY"
    _MODEL: str
    _CONTEXT_SIZE: int

    @classmethod
    def display_name(cls):
        return f"OpenAI/{cls._MODEL}"

    @property
    def context_size(self) -> int:
        return self._CONTEXT_SIZE

    def _call_api(self, prompt: str, chat_config):
        return f"I'm pretending to be {self._MODEL} from OpenAI"


class OpenaiGpt35Turbo16kLlm(OpenaiLlmApi):
    # https://platform.openai.com/docs/models/gpt-3-5
    _MODEL = "gpt-3.5-turbo-16k"
    _CONTEXT_SIZE = 16_384


@hookimpl(specname="ora_llm")
def openai_gpt_35_turbo_16k_llm():
    return OpenaiGpt35Turbo16kLlm


class OpenaiGpt4Llm(OpenaiLlmApi):
    # https://platform.openai.com/docs/models/gpt-4
    _MODEL = "gpt-4"
    _CONTEXT_SIZE = 8_192


@hookimpl(specname="ora_llm")
def openai_gpt_4_llm():
    return OpenaiGpt4Llm
