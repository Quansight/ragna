import dataclasses

from collections import deque
from typing import Iterable, Iterator, TypeVar

from ragna._backend import Page, Tokenizer

T = TypeVar("T")


# The function is adapted from more_itertools.windowed to allow a ragged last window
# https://more-itertools.readthedocs.io/en/stable/api.html#more_itertools.windowed
def _windowed_ragged(
    iterable: Iterable[T], *, n: int, step: int
) -> Iterator[tuple[T, ...]]:
    window = deque(maxlen=n)
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
    page_numbers: list[int] | None
    num_tokens: int


def chunk_pages(
    pages: Iterable[Page], *, chunk_size: int, chunk_overlap: int, tokenizer: Tokenizer
) -> Iterator[Chunk]:
    for window in _windowed_ragged(
        (
            (token, page.number)
            for page in pages
            for token in tokenizer.encode(page.text)
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
