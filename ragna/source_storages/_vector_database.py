import dataclasses
import itertools
from collections import deque
from typing import (
    Deque,
    Iterable,
    Iterator,
    Optional,
    TypeVar,
    cast,
)

from ragna._compat import itertools_pairwise
from ragna.core import (
    PackageRequirement,
    Page,
    Requirement,
    Source,
    SourceStorage,
)

@dataclasses.dataclass
class Chunk:
    text: str
    page_numbers: Optional[list[int]]
    document_id: int
    num_tokens: int


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

    def __init__(self) -> None:
        import chromadb.api
        # import chromadb.utils.embedding_functions

        # self._embedding_function = cast(
        #     chromadb.api.types.EmbeddingFunction,
        #     chromadb.utils.embedding_functions.DefaultEmbeddingFunction(),
        # )
        # https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2#all-minilm-l6-v2

    @classmethod
    def _page_numbers_to_str(cls, page_numbers: Optional[Iterable[int]]) -> str:
        if not page_numbers:
            return ""

        page_numbers = sorted(set(page_numbers))
        if len(page_numbers) == 1:
            return str(page_numbers[0])

        ranges_str = []
        range_int = []
        for current_page_number, next_page_number in itertools_pairwise(
            itertools.chain(sorted(page_numbers), [None])
        ):
            current_page_number = cast(int, current_page_number)

            range_int.append(current_page_number)
            if next_page_number is None or next_page_number > current_page_number + 1:
                ranges_str.append(
                    ", ".join(map(str, range_int))
                    if len(range_int) < 3
                    else f"{range_int[0]}-{range_int[-1]}"
                )
                range_int = []

        return ", ".join(ranges_str)

    @classmethod
    def _take_sources_up_to_max_tokens(
        cls, sources: Iterable[Source], *, max_tokens: int
    ) -> list[Source]:
        taken_sources = []
        total = 0
        for source in sources:
            new_total = total + source.num_tokens
            if new_total > max_tokens:
                break

            taken_sources.append(source)
            total = new_total

        return taken_sources
