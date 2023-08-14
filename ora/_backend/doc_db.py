import abc

from .component import Component


class DocDB(Component):
    @abc.abstractmethod
    def store(self, documents: list) -> None:
        ...

    @abc.abstractmethod
    def retrieve(self, prompt: str, *, chat_config) -> list:
        ...
