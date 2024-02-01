from enum import Enum, unique

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
