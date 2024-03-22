# import json
# from typing import AsyncIterator, cast

# from ragna.core import RagnaException, Source

from ragna.core import Assistant


class OllamaApiAssistant(Assistant):
    _MODEL: str

    @classmethod
    def display_name(cls) -> str:
        return f"Ollama/{cls._MODEL}"
