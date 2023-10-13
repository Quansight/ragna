import abc
from typing import Optional, Protocol, Sequence

from pydantic import BaseModel

from ._component import RagComponent
from ._document import Document


# FIXME: no need for this here
class Tokenizer(Protocol):
    def encode(self, text: str) -> list[int]:
        ...

    def decode(self, tokens: Sequence[int]) -> str:
        ...


class Source(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    id: str
    document: Document
    location: str
    content: Optional[str]
    num_tokens: Optional[int]


class SourceStorage(RagComponent, abc.ABC):
    __ragna_protocol_methods__ = ["store", "retrieve"]

    @abc.abstractmethod
    def store(self, documents: list[Document]) -> None:
        """Store content of documents.

        Args:
            documents: Documents to store
        """
        ...

    @abc.abstractmethod
    def retrieve(self, documents: list[Document], prompt: str) -> list[Source]:
        ...
