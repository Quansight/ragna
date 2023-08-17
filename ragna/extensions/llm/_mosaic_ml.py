from ragna.extensions import hookimpl

from ._llm_api import LlmApi


class MosaicMlLlmApi(LlmApi):
    _API_KEY_ENV_VAR = "MOSAIC_API_KEY"
    _MODEL: str
    _CONTEXT_SIZE: int

    @classmethod
    def display_name(cls):
        return f"Mosaic/{cls._MODEL}"

    @property
    def context_size(self) -> int:
        return self._CONTEXT_SIZE

    def _call_api(self, prompt: str, chat_config):
        return f"I'm pretending to be {self._MODEL} from Mosaic"


class MosaicMlMpt7bInstructLlm(MosaicMlLlmApi):
    # I couldn't find anything official
    # https://huggingface.co/mosaicml/mpt-7b-instruct#model-description
    _MODEL = "mpt-7b-instruct"
    _CONTEXT_SIZE = 2048


@hookimpl(specname="ragna_llm")
def mosaic_ml_mpt_7b_instruct_llm():
    return MosaicMlMpt7bInstructLlm


class MosaicMlMpt30bInstructLlm(MosaicMlLlmApi):
    # https://docs.mosaicml.com/en/latest/inference.html#text-completion-models
    _MODEL = "mpt-30b-instruct"
    _CONTEXT_SIZE = 8_192


@hookimpl(specname="ragna_llm")
def mosaic_ml_mpt_30b_instruct_llm():
    return MosaicMlMpt30bInstructLlm
