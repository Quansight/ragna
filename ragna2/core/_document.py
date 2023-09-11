from __future__ import annotations

import abc
import dataclasses
from pathlib import Path
from typing import Any, Iterator, Optional

from ._component import Component
from ._exceptions import RagnaException
from ._requirement import PackageRequirement, Requirement


class Document(abc.ABC):
    def __init__(
        self,
        *,
        id: Optional[str] = None,
        name: str,
        metadata: dict[str, Any],
        page_extractor: Optional[PageExtractor] = None,
    ):
        self.id = id
        self.name = name
        self.metadata = metadata

        if page_extractor is None:
            try:
                # FIXME:
                page_extractor = BUILTIN_PAGE_EXTRACTORS[Path(name).suffix]()
            except KeyError:
                raise RagnaException()
        self.page_extractor = page_extractor

    @abc.abstractmethod
    def read(self) -> bytes:
        ...

    def extract_pages(self):
        yield from self.page_extractor.extract_pages(
            name=self.name, content=self.read()
        )

    @classmethod
    def _from_data(cls, data):
        return cls(id=data.id, name=data.name, metadata=data.metadata_)


@dataclasses.dataclass
class Page:
    text: str
    number: Optional[int] = None


class PageExtractor(Component, abc.ABC):
    def __init__(self):
        # FIXME: this is an ugly hack. Since we subclass from Component, we would also
        #  need to provide a config. That is not possible right now
        pass

    @abc.abstractmethod
    def extract_pages(self, name: str, content: bytes) -> Iterator[Page]:
        ...


class PageExtractors(dict):
    def register(self, suffix: str):
        def decorator(cls):
            self[suffix] = cls
            return cls

        return decorator


BUILTIN_PAGE_EXTRACTORS = PageExtractors()


@BUILTIN_PAGE_EXTRACTORS.register(".txt")
class TxtPageExtractor(PageExtractor):
    def extract_pages(self, name: str, content: bytes) -> Iterator[Page]:
        yield Page(text=content.decode())


@BUILTIN_PAGE_EXTRACTORS.register(".pdf")
class PdfPageExtractor(PageExtractor):
    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [PackageRequirement("pymupdf")]

    def extract_pages(self, name: str, content: bytes) -> Iterator[Page]:
        import fitz

        with fitz.Document(stream=content, filetype=Path(name).suffix) as document:
            for number, page in enumerate(document, 1):
                yield Page(text=page.get_text(sort=True), number=number)
