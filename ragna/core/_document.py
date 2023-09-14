from __future__ import annotations

import abc
import dataclasses
from pathlib import Path
from typing import Any, Iterator, Optional

from ._exceptions import RagnaException
from ._requirement import PackageRequirement, Requirement, RequirementMixin


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
    def _from_state(cls, data):
        return cls(id=data.id, name=data.name, metadata=data.metadata_)

    def _to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "metadata": self.metadata,
        }


class LocalDocument(Document):
    def __init__(
        self,
        path: Optional[str | Path] = None,
        *,
        name: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        **kwargs,
    ):
        if metadata is None:
            metadata = {}
        metadata_path = metadata.get("path")

        if path is None and metadata_path is None:
            raise RagnaException()
        elif path is not None and metadata_path is not None:
            raise RagnaException()
        elif metadata_path is not None:
            path = metadata_path
        else:
            metadata["path"] = str(path)
        if name is None:
            name = Path(path).name
        super().__init__(name=name, metadata=metadata, **kwargs)

    @property
    def path(self) -> Path:
        return Path(self.metadata["path"])

    def read(self) -> bytes:
        with open(self.path, "rb") as stream:
            return stream.read()


@dataclasses.dataclass
class Page:
    text: str
    number: Optional[int] = None


class PageExtractor(RequirementMixin, abc.ABC):
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
