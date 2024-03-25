from ragna.core import Chunk, Embedding, EmbeddingModel


class MiniLML6v2(EmbeddingModel):
    def __init__(self):
        super().__init__()
        from chromadb.utils import embedding_functions
        self.model = embedding_functions.DefaultEmbeddingFunction()

    def embed_chunks(self, chunks: list[Chunk]) -> list[Embedding]:
        return [Embedding(embed_chunk[0], embed_chunk[1]) for embed_chunk in zip(self.embed_text([chunk.text for chunk in chunks]), chunks)]

    def embed_text(self, text: list[str]) -> list[float]:
        return self.model(text)
