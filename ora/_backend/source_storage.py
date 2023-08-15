import abc

import dataclasses

from .component import Component
from .document import Document


@dataclasses.dataclass
class Source:
    name: str
    location: str
    text: str


class SourceStorage(Component, abc.ABC):
    @abc.abstractmethod
    def store(self, documents: list[Document], app_config, chat_config) -> None:
        ...

    @abc.abstractmethod
    def retrieve(self, prompt: str, *, app_config, chat_config) -> list[Source]:
        ...
