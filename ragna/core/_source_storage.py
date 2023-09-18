import abc
from typing import Protocol, Sequence

from ._component import RagComponent
from ._core import RagnaException, RagnaId
from ._document import Document


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
        id: RagnaId,
        document_id: RagnaId,
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


class SourceStorage(RagComponent, abc.ABC):
    __ragna_protocol_methods__ = ["store", "retrieve"]

    @abc.abstractmethod
    def store(self, documents: list[Document]) -> None:
        ...

    @abc.abstractmethod
    def retrieve(self, prompt: str) -> list[Source]:
        ...
