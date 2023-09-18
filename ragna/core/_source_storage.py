import abc
import dataclasses
from typing import Protocol, Sequence

from ._component import RagComponent
from ._core import RagnaId
from ._document import Document


class Tokenizer(Protocol):
    def encode(self, text: str) -> list[int]:
        ...

    def decode(self, tokens: Sequence[int]) -> str:
        ...


@dataclasses.dataclass
class Source:
    id: RagnaId
    document_id: RagnaId
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
