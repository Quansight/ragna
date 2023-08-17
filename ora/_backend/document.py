from __future__ import annotations

import abc
import dataclasses

from pathlib import Path
from typing import Collection, Iterator

from .component import Component
from .utils import compute_id


@dataclasses.dataclass
class Page:
    text: str
    number: int | None = None


class PageExtractor(Component, abc.ABC):
    SUFFIX: Collection[str] | str = ""

    def can_handle(self, name: str, content: bytes) -> bool:
        if not self.SUFFIX:
            # FIXME: use logging
            print("ADDME")
            raise SystemExit(1)

        suffix = Path(name).suffix
        if isinstance(self.SUFFIX, str):
            return suffix == self.SUFFIX
        else:
            return suffix in self.SUFFIX

    @abc.abstractmethod
    def extract_pages(self, content: bytes) -> Iterator[Page]:
        ...


@dataclasses.dataclass
class DocumentMetadata(Component):
    name: str
    id: str

    @classmethod
    def from_name(cls, name: str) -> DocumentMetadata:
        return cls(name, compute_id(name))


@dataclasses.dataclass
class Document:
    content: bytes
    metadata: DocumentMetadata
    page_extractor: PageExtractor

    @classmethod
    def _from_name_and_content(
        cls,
        name: str,
        content: bytes,
        *,
        page_extractors: list[PageExtractor],
    ) -> Document:
        try:
            page_extractor = next(
                p for p in page_extractors if p.can_handle(name, content)
            )
        except StopIteration:
            # FIXME: use logging
            print(
                f"No registered PageExtractor (ora_page_extractor) is able to handle "
                f"{name}"
            )
            raise SystemExit(1)

        return cls(
            content=content,
            metadata=DocumentMetadata.from_name(name),
            page_extractor=page_extractor,
        )

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def id(self) -> str:
        return self.metadata.id

    def extract_pages(self) -> Iterator[Page]:
        yield from self.page_extractor.extract_pages(self.content)
