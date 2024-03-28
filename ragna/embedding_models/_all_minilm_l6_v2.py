from typing import Union

from ragna.core import (
    Chunk,
    Embedding,
    EmbeddingModel,
    PackageRequirement,
    Requirement,
)


class AllMiniLML6v2(EmbeddingModel):
    @classmethod
    def display_name(cls) -> str:
        return "all-MiniLM-L6-v2"

    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [
            # Rather than using sentence transformers package by itself, chromadb
            # packaged this embedding model and is a much lighter dependency.
            PackageRequirement("chromadb>=0.4.13"),
            PackageRequirement("tiktoken"),
        ]

    def __init__(self) -> None:
        super().__init__()
        from chromadb.utils import embedding_functions

        self._model = embedding_functions.ONNXMiniLM_L6_V2()

    def embed_chunks(self, chunks: list[Chunk]) -> list[Embedding]:
        return [
            Embedding(values=self._embed_text(chunk.text), chunk=chunk)
            for chunk in chunks
        ]

    def _embed_text(
        self, text: Union[list[str], str]
    ) -> Union[list[list[float]], list[float]]:
        if isinstance(text, str):
            return self._model([text])[0]
        else:
            return self._model(text)
