from enum import Enum, unique

from ragna.core import Source

from ._api import ApiAssistant


@unique
class AI2LabsModelType(str, Enum):
    light = "light"
    mid = "mid"
    ultra = "ultra"


class AI21LabsAssistant(ApiAssistant):
    _API_KEY_ENV_VAR = "AI21LABS_API_KEY"
    _MODEL_TYPE: str
    _CONTEXT_SIZE: int = 8_192

    @classmethod
    def display_name(cls) -> str:
        return f"AI21Labs/jurassic-2-{cls._MODEL_TYPE}"

    @property
    def max_input_size(self) -> int:
        return self._CONTEXT_SIZE

    def _make_system_content(self, sources: list[Source]) -> str:
        instruction = (
            "You are a helpful assistant that answers user questions given the context below. "
            "If you don't know the answer, just say so. Don't try to make up an answer. "
            "Only use the sources below to generate the answer."
        )
        return instruction + "\n\n".join(source.content for source in sources)
