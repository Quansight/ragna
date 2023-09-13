import abc

from ._component import Component
from ._source_storage import Source


class Llm(Component, abc.ABC):
    __ragna_protocol_methods__ = ["complete"]

    @property
    @abc.abstractmethod
    def context_size(self) -> int:
        ...

    @abc.abstractmethod
    def complete(self, prompt: str, sources: list[Source]) -> str:
        ...
