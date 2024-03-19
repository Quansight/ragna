from ragna.core import Chunk

from ragna.core._components import Embedding, GenericEmbeddingModel


class MiniLML6v2(GenericEmbeddingModel):

    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

    def embed_chunks(self, chunks: list[Chunk]) -> list[Embedding]:
        return [Embedding(self.embed_text(chunk.text), chunk) for chunk in chunks]

    def embed_text(self, text: str) -> list[float]:
        return self.model.encode(text).tolist()