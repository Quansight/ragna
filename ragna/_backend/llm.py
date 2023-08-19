import abc

from .component import Component
from .source_storage import Source


class Llm(Component, abc.ABC):
    @property
    @abc.abstractmethod
    def context_size(self) -> int:
        ...

    @abc.abstractmethod
    def complete(self, prompt: str, sources: list[Source], *, chat_config) -> str:
        ...
