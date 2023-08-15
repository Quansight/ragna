import abc

import dataclasses

from .component import Component
from .doc_meta import Doc


@dataclasses.dataclass
class Source:
    name: str
    location: str
    text: str


class DocDB(Component, abc.ABC):
    @abc.abstractmethod
    def store(self, documents: list[Doc], app_config, chat_config) -> None:
        ...

    @abc.abstractmethod
    def retrieve(self, prompt: str, *, app_config, chat_config) -> list[Source]:
        ...
