from ragna.core import Document, Chunk, ChunkingModel

import functools

from typing import TYPE_CHECKING, TypeVar, Iterable, Iterator, Deque

from collections import deque

if TYPE_CHECKING:
    import tiktoken

T = TypeVar("T")


# The function is adapted from more_itertools.windowed to allow a ragged last window
# https://more-itertools.readthedocs.io/en/stable/api.html#more_itertools.windowed
def _windowed_ragged(
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

class GenericChunkingModel(ChunkingModel):
    def chunk_documents(self, documents: list[Document], chunk_size: int = 500, chunk_overlap: int = 250) -> list[Chunk]:
        chunks = []
        for document in documents:
            for window in _windowed_ragged(
                    (
                            (tokens, page.number)
                            for page in document.extract_pages()
                            for tokens in self.tokenizer.encode(page.text)
                    ),
                    n=chunk_size,
                    step=chunk_size - chunk_overlap,
            ):
                tokens, page_numbers = zip(*window)
                chunks.append(Chunk(
                    text=self.tokenizer.decode(tokens),  # type: ignore[arg-type]
                    document_id=document.id,
                    page_numbers=list(filter(lambda n: n is not None, page_numbers)) or None,
                    num_tokens=len(tokens),
                ))

        return chunks
