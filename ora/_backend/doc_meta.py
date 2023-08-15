from __future__ import annotations

import abc
import dataclasses

import hashlib
from pathlib import Path
from typing import Type

from .component import Component


@dataclasses.dataclass
class Page:
    text: str
    number: int | None = None


class DocMeta(Component, abc.ABC):
    def __init__(self, name: str, id: str) -> None:
        self.name = name
        self.id = id

    @property
    @abc.abstractmethod
    def suffix(self) -> str:
        ...

    @abc.abstractmethod
    def extract_pages(self, content: bytes) -> list[Page]:
        ...


@dataclasses.dataclass
class Doc:
    meta: DocMeta
    content: bytes

    @classmethod
    def _from_name_and_content(
        cls,
        name: str,
        content: bytes,
        *,
        available_doc_meta_types: dict[str, Type[DocMeta]],
    ) -> Doc:
        # We don't need to guard against a missing key here, because we only allow
        # uploading documents of the available types in the first place.
        doc_meta_type = available_doc_meta_types[Path(name).suffix]
        return cls(
            meta=doc_meta_type(
                name=name,
                # Since this is just for an internal ID and, although some where found,
                # collisions are incredibly rare, we are ok using a weak-ish but fast
                # algorithm here.
                id=hashlib.md5(content).hexdigest(),
            ),
            content=content,
        )

    @property
    def name(self) -> str:
        return self.meta.name

    @property
    def id(self) -> str:
        return self.meta.id

    def extract_pages(self) -> list[Page]:
        return self.meta.extract_pages(self.content)
