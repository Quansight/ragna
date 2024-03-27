from collections import deque
from typing import (
    Deque,
    Iterable,
    Iterator,
    TypeVar,
    Union,
)
from uuid import UUID

from ragna.core import (
    Chunk,
    Document,
    Embedding,
    EmbeddingModel,
    PackageRequirement,
    Page,
    Requirement,
)

T = TypeVar("T")


# The function is adapted from more_itertools.windowed to allow a ragged last window
# https://more-itertools.readthedocs.io/en/stable/api.html#more_itertools.windowed
def windowed_ragged(
    iterable: Iterable[T], *, n: int, step: int
) -> Iterator[tuple[T, ...]]:
    window: Deque[T] = deque(maxlen=n)
    i = n
    for _ in map(window.append, iterable):
        i -= 1
        if not i:
            i = step
            yield tuple(window)

    if len(window) < n:
        yield tuple(window)
    elif 0 < i < min(step, n):
        yield tuple(window)[i:]


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
        import tiktoken
        from chromadb.utils import embedding_functions

        self._tokenizer = tiktoken.get_encoding("cl100k_base")
        self._model = embedding_functions.ONNXMiniLM_L6_V2()

    def embed_documents(self, documents: list[Document]) -> list[Embedding]:
        return [
            Embedding(embedding=self.embed_text(chunk.text), chunk=chunk)
            for document in documents
            for chunk in self._chunk_pages(
                document.extract_pages(),
                document_id=document.id,
                chunk_size=500,
                chunk_overlap=250,
            )
        ]

    def embed_text(
        self, text: Union[list[str], str]
    ) -> Union[list[list[float]], list[float]]:
        if isinstance(text, str):
            return self._model([text])[0]
        else:
            return self._model(text)

    def _chunk_pages(
        self,
        pages: Iterable[Page],
        document_id: UUID,
        *,
        chunk_size: int,
        chunk_overlap: int,
    ) -> Iterator[Chunk]:
        for window in windowed_ragged(
            (
                (tokens, page.number)
                for page in pages
                for tokens in self._tokenizer.encode(page.text)
            ),
            n=chunk_size,
            step=chunk_size - chunk_overlap,
        ):
            tokens, page_numbers = zip(*window)
            yield Chunk(
                text=self._tokenizer.decode(tokens),  # type: ignore[arg-type]
                document_id=document_id,
                page_numbers=list(filter(lambda n: n is not None, page_numbers))
                or None,
                num_tokens=len(tokens),
            )
