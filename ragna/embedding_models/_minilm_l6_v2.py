from ragna.core import Chunk, Embedding, EmbeddingModel, Requirement, PackageRequirement


class MiniLML6v2(EmbeddingModel):

    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [
            # Rather than using sentence transformers by itself, the embedding functions module of chroma
            # Can be used instead as it is a much lighter weight dependency
            PackageRequirement("chromadb>=0.4.13"),
            PackageRequirement("tiktoken"),
        ]

    def __init__(self):
        super().__init__()
        from chromadb.utils import embedding_functions
        self.model = embedding_functions.DefaultEmbeddingFunction()

    def embed_chunks(self, chunks: list[Chunk]) -> list[Embedding]:
        return [Embedding(embed_chunk[0], embed_chunk[1]) for embed_chunk in zip(self.embed_text([chunk.text for chunk in chunks]), chunks)]

    def embed_text(self, text: list[str]) -> list[float]:
        return self.model(text)
