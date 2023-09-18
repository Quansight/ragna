import abc

import enum

from typing import Optional

from ._component import RagComponent
from ._core import RagnaId
from ._source_storage import Source


class MessageRole(enum.Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


# while live, each source needs to have content
# after reconstructing, this is gone
# how do we model this?


class Message:
    def __init__(
        self,
        *,
        id: RagnaId,
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


class Assistant(RagComponent, abc.ABC):
    __ragna_protocol_methods__ = ["answer"]

    @property
    @abc.abstractmethod
    def max_input_size(self) -> int:
        ...

    @abc.abstractmethod
    def answer(self, prompt: str, sources: list[Source]) -> Message:
        ...
