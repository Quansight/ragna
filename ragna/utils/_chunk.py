import dataclasses

from collections import deque
from typing import Deque, Iterable, Iterator, Optional, Protocol, Sequence, TypeVar

from ragna.core import Page

T = TypeVar("T")


class Tokenizer(Protocol):
    def encode(self, text: str) -> list[int]:
        ...

    def decode(self, tokens: Sequence[int]) -> str:
        ...


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


@dataclasses.dataclass
class Chunk:
    text: str
    page_numbers: Optional[list[int]]
    num_tokens: int


def chunk_pages(
    pages: Iterable[Page], *, chunk_size: int, chunk_overlap: int, tokenizer: Tokenizer
) -> Iterator[Chunk]:
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
            text=tokenizer.decode(tokens),
            page_numbers=list(filter(lambda n: n is not None, page_numbers)) or None,
            num_tokens=len(tokens),
        )
