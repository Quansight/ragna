from abc import ABC, abstractmethod

from sentence_transformers import SentenceTransformer
import torch

from ragna.core._components import Component

from ragna.source_storages._vector_database import Chunk

device = 'cuda' if torch.cuda.is_available() else 'cpu'


class Embedding:
    embedding: list[float]
    chunk: Chunk

    def __init__(self, embedding: list[float], chunk: Chunk):
        super().__init__()
        self.embedding = embedding
        self.chunk = chunk


class GenericEmbeddingModel(Component, ABC):
    _EMBEDDING_DIMENSIONS: int

    @abstractmethod
    def embed_chunks(self, chunks: list[Chunk]) -> list[Embedding]:
        raise NotImplementedError

    def embed_text(self, text: str) -> list[float]:
        raise NotImplementedError

    def get_embedding_dimensions(self):
        return self._EMBEDDING_DIMENSIONS


class MiniLML6v2(GenericEmbeddingModel):
    _EMBEDDING_DIMENSIONS = 384

    def __init__(self):
        self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', device=device)

    def embed_chunks(self, chunks: list[Chunk]) -> list[Embedding]:
        return [Embedding(self.embed_text(chunk.text), chunk) for chunk in chunks]

    def embed_text(self, text: str) -> list[float]:
        return self.model.encode(text).tolist()