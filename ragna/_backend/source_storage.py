import abc

import dataclasses

from typing import Protocol, Sequence

from .component import Component
from .document import Document


class Tokenizer(Protocol):
    def encode(self, text: str) -> list[int]:
        ...

    def decode(self, tokens: Sequence[int]) -> str:
        ...


@dataclasses.dataclass
class Source:
    document_name: str
    page_numbers: str
    text: str
    num_tokens: int


class SourceStorage(Component, abc.ABC):
    @abc.abstractmethod
    def store(self, documents: list[Document], app_config, chat_config) -> None:
        ...

    @abc.abstractmethod
    def retrieve(self, prompt: str, *, app_config, chat_config) -> list[Source]:
        ...
