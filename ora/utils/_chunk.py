import dataclasses
from typing import Sequence

from ora._backend import Page


@dataclasses.dataclass
class Chunk:
    text: str
    page_numbers: list[int] | None
    num_tokens: int


def chunk_pages(
    pages: Sequence[Page], *, chunk_size: int, chunk_overlap: int, tokenizer: str
) -> list[Chunk]:
    # FIXME
    page = pages[0]
    return [Chunk(page.text, page.number, chunk_size)]
