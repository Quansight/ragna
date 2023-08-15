import abc

from .component import Component


class LLM(Component, abc.ABC):
    @property
    @abc.abstractmethod
    def context_size(self) -> int:
        ...

    @abc.abstractmethod
    def complete(self, prompt: str, chat_config):
        ...
