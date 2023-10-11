import abc
from typing import Protocol, Sequence

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
    document_name: str
    location: str
    content: str
    num_tokens: int


class SourceStorage(RagComponent, abc.ABC):
    __ragna_protocol_methods__ = ["store", "retrieve"]

    @abc.abstractmethod
    def store(self, documents: list[Document]) -> None:
        ...

    @abc.abstractmethod
    def retrieve(self, prompt: str) -> list[Source]:
        ...
