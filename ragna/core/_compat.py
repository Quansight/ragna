"""
Temporary module
"""

import functools
import uuid
from collections import deque
from typing import TYPE_CHECKING, Deque, Iterable, Iterator, TypeVar

from ._document import Chunk, Page

if TYPE_CHECKING:
    import tiktoken

__all__ = ["chunk_pages"]

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


@functools.cache
def _get_tokenizer() -> "tiktoken.Encoding":
    import tiktoken

    return tiktoken.get_encoding("cl100k_base")


def chunk_pages(
    pages: Iterable[Page],
    document_id: uuid.UUID,
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> Iterator[Chunk]:
    tokenizer = _get_tokenizer()

    for window in _windowed_ragged(
        (
            (tokens, page.number)
            for page in pages
            for tokens in tokenizer.encode(page.text)
        ),
        n=chunk_size,
        step=chunk_size - chunk_overlap,
    ):
        tokens, page_numbers = zip(*window)
        yield Chunk(
            text=tokenizer.decode(tokens),  # type: ignore[arg-type]
            document_id=document_id,
            page_numbers=list(filter(lambda n: n is not None, page_numbers)) or None,
            num_tokens=len(tokens),
        )
