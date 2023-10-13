import abc

import uuid
from typing import Protocol, Sequence

from ._components import Component
from ._document import Document
from ._utils import RagnaException


# FIXME: no need for this here
class Tokenizer(Protocol):
    def encode(self, text: str) -> list[int]:
        ...

    def decode(self, tokens: Sequence[int]) -> str:
        ...


class Source:
    def __init__(
        self,
        *,
        id: uuid.UUID,
        document_id: uuid.UUID,
        document_name: str,
        location: str,
        content: str,
        num_tokens: int,
    ):
        self.id = id
        self.document_id = document_id
        self.document_name = document_name
        self.location = location
        self.content = content
        self.num_tokens = num_tokens


class ReconstructedSource(Source):
    def __init__(self, **kwargs):
        if any(
            kwargs.setdefault(param, None) is not None
            for param in ["content", "num_tokens"]
        ):
            raise RagnaException
        super().__init__(**kwargs)


class SourceStorage(Component, abc.ABC):
    __ragna_protocol_methods__ = ["store", "retrieve"]

    @abc.abstractmethod
    def store(self, documents: list[Document]) -> None:
        """Store content of documents.

        Args:
            documents: Documents to store
        """
        ...

    @abc.abstractmethod
    def retrieve(self, prompt: str) -> list[Source]:
        ...
