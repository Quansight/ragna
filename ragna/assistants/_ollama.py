# import json
# from typing import AsyncIterator, cast

from ragna.core import Source  # RagnaException

from ragna.core import Assistant


class OllamaApiAssistant(Assistant):
    _MODEL: str

    @classmethod
    def display_name(cls) -> str:
        return f"Ollama/{cls._MODEL}"

    def _make_system_content(self, sources: list[Source]) -> str:
        instruction = (
            "You are an helpful assistants that answers user questions given the context below. "
            "If you don't know the answer, just say so. Don't try to make up an answer. "
            "Only use the following sources to generate the answer."
        )
        return instruction + "\n\n".join(source.content for source in sources)
