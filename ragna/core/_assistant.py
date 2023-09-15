import abc

import enum

from typing import Optional

from ._component import RagComponent
from ._source_storage import Source


class MessageRole(enum.Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class Message:
    def __init__(
        self,
        *,
        id: str,
        content: str,
        role: MessageRole,
        sources: Optional[list[Source]] = None,
    ):
        self.id = id
        self.content = content
        self.role = role
        self.sources = sources or []

    def __str__(self):
        return self.content

    @classmethod
    def _from_state(cls, data):
        return cls(
            content=data.content,
            role=MessageRole[data.role],
            sources=[Source._from_state(s) for s in data.source_datas],
        )


# FIXME: context_size -> max_input_size


class Assistant(RagComponent, abc.ABC):
    __ragna_protocol_methods__ = ["answer"]

    @property
    @abc.abstractmethod
    def context_size(self) -> int:
        ...

    @abc.abstractmethod
    def answer(self, prompt: str, sources: list[Source]) -> Message:
        ...
