import abc
import dataclasses
from typing import Protocol, Sequence

from ._component import Component
from ._document import Document


class Tokenizer(Protocol):
    def encode(self, text: str) -> list[int]:
        ...

    def decode(self, tokens: Sequence[int]) -> str:
        ...


@dataclasses.dataclass
class Source:
    document_id: str
    document_name: str
    page_numbers: str
    text: str
    num_tokens: int


class SourceStorage(Component, abc.ABC):
    __ragna_protocol_methods__ = ["store", "retrieve"]

    @abc.abstractmethod
    def store(self, documents: list[Document]) -> None:
        ...

    @abc.abstractmethod
    def retrieve(self, prompt: str) -> list[Source]:
        ...
