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


# FIXME: Rethink this, since it is different from the other components
# We actually need to or we need to construct Document with appconfig as well
class DocumentMetadata(Component, abc.ABC):
    def __init__(self, app_config, name: str, id: str) -> None:
        super().__init__(app_config)
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
class Document:
    metadata: DocumentMetadata
    content: bytes

    @classmethod
    def _from_name_and_content(
        cls,
        name: str,
        content: bytes,
        *,
        available_document_metadata_types: dict[str, Type[DocumentMetadata]],
    ) -> Document:
        # We don't need to guard against a missing key here, because we only allow
        # uploading documents of the available types in the first place.
        document_metadata = available_document_metadata_types[Path(name).suffix]
        return cls(
            metadata=document_metadata(
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
        return self.metadata.name

    @property
    def id(self) -> str:
        return self.metadata.id

    def extract_pages(self) -> list[Page]:
        return self.metadata.extract_pages(self.content)
