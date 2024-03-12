from abc import ABC, abstractmethod

import tiktoken

from ragna.core import (
    Document,
)
from ragna.source_storages._vector_database import Chunk

from ragna.core import Page, Document, Component

from collections import deque

from typing import Iterable, Iterator, Deque, TypeVar


class GenericChunkingModel(Component, ABC):
    def __init__(self):
        # we need a way of estimating tokens that is common to all chunking models
        self._tokenizer = tiktoken.get_encoding("cl100k_base")
    @abstractmethod
    def chunk_documents(self, documents: list[Document]) -> list[Chunk]:
        raise NotImplementedError


class NLTKChunkingModel(GenericChunkingModel):
    def __init__(self):
        super().__init__()

        # our text splitter goes here
        from langchain.text_splitter import NLTKTextSplitter
        self.text_splitter = NLTKTextSplitter()

    def chunk_documents(self, documents: list[Document]) -> list[Chunk]:
        # Problem: chunk need to preserve its page number
        chunks = []
        for document in documents:
            for page in document.extract_pages():
                chunks_raw = self.text_splitter.split_text(page.text)
                chunks += [Chunk(page_numbers=[page.number], text=chunk, document_id=document.id, num_tokens=len(self._tokenizer.encode(chunk))) for chunk in chunks_raw]
        return chunks


class SpacyChunkingModel(GenericChunkingModel):
    def __init__(self):
        super().__init__()

        from langchain_text_splitters import SpacyTextSplitter
        self.text_splitter = SpacyTextSplitter()

    # TODO: This needs to keep track of the pages
    def chunk_documents(self, documents: list[Document]) -> list[Chunk]:
        # Problem: chunk need to preserve its page number
        chunks = []
        for document in documents:
            for page in document.extract_pages():
                chunks_raw = self.text_splitter.split_text(page.text)
                chunks += [Chunk(page_numbers=[page.number], text=chunk, document_id=document.id,
                                 num_tokens=len(self._tokenizer.encode(chunk))) for chunk in chunks_raw]
        return chunks


T = TypeVar("T")


class TokenChunkingModel(GenericChunkingModel):
    def chunk_documents(self, documents: list[Document], chunk_size: int = 512, chunk_overlap: int = 128) -> list[Chunk]:
        chunks = []
        for document in documents:
            chunks += self._chunk_pages(document.id, document.extract_pages(), chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        return chunks

    def _chunk_pages(
            self, document_id: int, pages: Iterable[Page], *, chunk_size: int, chunk_overlap: int
    ) -> Iterator[Chunk]:
        for window in TokenChunkingModel._windowed_ragged(
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
                document_id=document_id,
                text=self._tokenizer.decode(tokens),  # type: ignore[arg-type]
                page_numbers=list(filter(lambda n: n is not None, page_numbers))
                             or None,
                num_tokens=len(tokens),
            )

    # The function is adapted from more_itertools.windowed to allow a ragged last window
    # https://more-itertools.readthedocs.io/en/stable/api.html#more_itertools.windowed
    @classmethod
    def _windowed_ragged(
            cls, iterable: Iterable[T], *, n: int, step: int
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