from typing import cast

from ragna.core import Config, PackageRequirement, Requirement, SourceStorage
from ragna.utils import Tokenizer


class VectorDatabaseSourceStorage(SourceStorage):
    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [
            # This looks like this should only be a requirement for Chroma, but it is
            # not. Chroma solved one major UX painpoint of vector DBs: the need for an
            # embedding function. Normally, one would pull in a massive amount
            # (in numbers as well as in size) of transitive dependencies that are hard
            # to manage and mostly not even used by the vector DB. Chroma provides a
            # wrapper around a compiled embedding function that has only minimal
            # requirements. We use this as base for all of our Vector DBs.
            PackageRequirement("chromadb>=0.4.13"),
            PackageRequirement("tiktoken"),
        ]

    def __init__(self, config: Config):
        super().__init__(config)

        import chromadb.utils.embedding_functions
        import tiktoken

        self._embedding_function = (
            chromadb.utils.embedding_functions.DefaultEmbeddingFunction()
        )
        # https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2#all-minilm-l6-v2
        self._embedding_dimensions = 384
        self._tokenizer = cast(Tokenizer, tiktoken.get_encoding("cl100k_base"))
