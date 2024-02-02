from ragna.core import Source

from ._api import ApiAssistant


class CohereApiAssistant(ApiAssistant):
    _API_KEY_ENV_VAR = "COHERE_API_KEY"
    _MODEL: str
    _CONTEXT_SIZE: int

    @classmethod
    def display_name(cls) -> str:
        return f"Cohere/{cls._MODEL}"

    @property
    def max_input_size(self) -> int:
        return self._CONTEXT_SIZE

    def _make_system_content(self) -> str:
        instruction = (
            "You are a helpful assistant that answers user questions given the included context. "
            "If you don't know the answer, just say so. Don't try to make up an answer. "
            "Only use the included documents below to generate the answer."
        )
        return instruction

    def _make_source_documents(self, sources: list[Source]) -> list[dict[str, str]]:
        document_sources = [
            {"title": source.id, "snippet": source.content} for source in sources
        ]
        return document_sources
