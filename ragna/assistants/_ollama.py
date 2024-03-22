# import json
# from typing import AsyncIterator, cast

# from ragna.core import RagnaException, Source

from ._api import ApiAssistant


class OllamaApiAssistant(ApiAssistant):
    _MODEL: str

    @classmethod
    def display_name(cls) -> str:
        return f"Ollama/{cls._MODEL}"
