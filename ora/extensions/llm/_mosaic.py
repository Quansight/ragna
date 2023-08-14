from ora.extensions import hookimpl

from ._llm_api import LlmApi


class MosaidLlmApi(LlmApi):
    _API_KEY_ENV_VAR = "MOSAIC_API_KEY"
    _MODEL: str
    _CONTEXT_SIZE: int

    @classmethod
    def name(cls):
        return f"Mosaic/{cls._MODEL}"

    @property
    def context_size(self) -> int:
        return self._CONTEXT_SIZE

    def _call_api(self, prompt: str, chat_config):
        return f"I'm pretending to be {self._MODEL} from Mosaic"


class MosaicMpt7bInstruct(MosaidLlmApi):
    # I couldn't find anything official
    # https://huggingface.co/mosaicml/mpt-7b-instruct#model-description
    _MODEL = "mpt-7b-instruct"
    _CONTEXT_SIZE = 2048


@hookimpl(specname="ora_llm")
def mosaic_mpt_7b_instruct():
    return MosaicMpt7bInstruct


class MosaicMpt30bInstruct(MosaidLlmApi):
    # https://docs.mosaicml.com/en/latest/inference.html#text-completion-models
    _MODEL = "mpt-30b-instruct"
    _CONTEXT_SIZE = 8_192


@hookimpl(specname="ora_llm")
def mosaic_mpt_30b_instruct():
    return MosaicMpt30bInstruct
